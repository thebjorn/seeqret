"""GUI-facing facade over the seeqret core.

   This is the only module in ``seeqret.gui`` that imports from the
   core packages (``storage``, ``models``, ``run_utils``...). Each
   method corresponds to one of jseeqret's IPC channels, so the two
   GUIs stay conceptually aligned.

   No chdir is needed: ``SqliteStorage.connection()`` and
   ``Secret.value`` both resolve the vault through
   ``get_seeqret_dir()`` (the ``SEEQRET`` env var), not the CWD.
   ``switch_vault`` re-points that env var, which is why the facade
   never caches derived state.
"""
import contextlib
import io
import os
import sys
import time
from pathlib import Path

from .. import __version__, merge, onboarding, vault_registry
from ..errors import SeeqretError
from ..filterspec import FilterSpec
from ..models import Secret, User
from ..run_utils import (
    get_seeqret_dir,
    is_initialized,
    qualified_user,
)
from ..seeqret_init import secrets_init
from ..seeqret_transfer import (
    resolve_recipients,
    resolve_user,
    vault_private_key,
)
from ..seeqrypt.nacl_backend import fingerprint
from ..serializers.jsoncrypt_serializer import JsonCryptSerializer
from ..serializers.serializer import SERIALIZERS
from ..slack import config as slack_config
from ..slack.identity import (
    bind_slack_handle,
    compute_fingerprint,
    require_verified_binding,
)
from ..slack.selftest import transport_selftest
from ..slack.session import slack_ctx, slack_session_status
from ..slack.transport import send_blob
from ..storage.sqlite_storage import SqliteStorage


class VaultFacade:
    """In-process replacement for jseeqret's IPC surface.
    """

    def __init__(self):
        self.storage = SqliteStorage()
        self._pending_merge = None

    # ---- vault:status ------------------------------------------------

    def vault_status(self) -> dict:
        """Vault availability + identity summary (cf. ``vault:status``).
        """
        initialized = is_initialized()
        status = dict(
            initialized=initialized,
            vault_dir=get_seeqret_dir() if 'SEEQRET' in os.environ else None,
            current_user=qualified_user(),
            version=__version__,
            owner=None,
            onboarding_active=False,
        )
        if initialized:
            admin = self.storage.fetch_admin()
            if admin:
                status['owner'] = admin.username
            try:
                status['onboarding_active'] = \
                    onboarding.wizard_active(self.storage)
            except Exception:
                pass
        return status

    # ---- secrets:* ---------------------------------------------------

    def list_secrets(self, filterspec: str = '*:*:*') -> list[dict]:
        """Decrypted secrets matching a glob filter (cf. ``secrets:list``).
        """
        filters = FilterSpec(filterspec).to_filterdict()
        return [s.to_plaintext_dict()
                for s in self.storage.fetch_secrets(**filters)]

    def add_secret(self, app: str, env: str, key: str,
                   value: str, type: str = 'str') -> None:
        """Encrypt and store a new secret (cf. ``secrets:add``).
        """
        secret = Secret(app=app, env=env, key=key,
                        plaintext_value=value, type=type)
        self.storage.add_secret(secret)

    def update_secret_value(self, app: str, env: str, key: str,
                            value: str, type: str = 'str') -> None:
        """Change the value of an existing secret (cf. ``secrets:update``).

           The identity (app, env, key) is immutable, mirroring
           jseeqret's edit dialog.
        """
        secret = Secret(app=app, env=env, key=key,
                        plaintext_value=value, type=type)
        self.storage.update_secret(secret)

    def remove_secret(self, app: str, env: str, key: str) -> None:
        """Delete a single secret (cf. ``secrets:remove``).
        """
        self.storage.remove_secrets(app=app, env=env, key=key)

    # ---- users:* -----------------------------------------------------

    def list_users(self) -> list[dict]:
        """Users with fingerprint and owner flag (cf. ``users:list``).
        """
        admin = self.storage.fetch_admin()
        owner_name = admin.username if admin else None
        res = []
        for user in self.storage.fetch_users():
            rec = user.__json__()
            rec['fingerprint'] = fingerprint(user.pubkey.encode('utf-8'))
            rec['is_owner'] = user.username == owner_name
            res.append(rec)
        return res

    def user_fingerprint(self, username: str) -> str:
        """The 5-char pubkey fingerprint for a user (link ceremony).
        """
        user = self.storage.fetch_user(username)
        if user is None:
            raise SeeqretError(f'unknown user: {username}')
        return compute_fingerprint(user)

    def add_user(self, username: str, email: str, pubkey: str,
                 name: str | None = None) -> None:
        self.storage.add_user(User(username, email, pubkey, name=name))

    def remove_user(self, username: str) -> None:
        """Delete a user; the vault owner is protected.
        """
        admin = self.storage.fetch_admin()
        if admin and admin.username == username:
            raise SeeqretError('cannot delete the vault owner')
        self.storage.remove_user(username)

    def link_slack(self, username: str, handle: str,
                   fingerprint_input: str) -> str:
        """Bind a Slack handle after the OOB fingerprint ceremony.

           The typed-back fingerprint is re-validated here (the GUI
           input is UX, not authority), mirroring jseeqret.
        """
        expected = self.user_fingerprint(username)
        if fingerprint_input.strip() != expected:
            raise SeeqretError('fingerprint confirmation mismatch')
        bind_slack_handle(self.storage, username, handle)
        return expected

    # ---- secrets:export ----------------------------------------------

    def serializers(self) -> list[str]:
        return sorted(SERIALIZERS)

    def recipients_grouped(self) -> list[dict]:
        """Users grouped by display name; selecting a group fans out
           to every machine identity sharing it (cf. ExportView).
        """
        groups = {}
        for user in self.storage.fetch_users():
            label = user.name or user.username
            groups.setdefault(label, []).append(user.username)
        return [dict(label=label, members=members)
                for label, members in sorted(groups.items())]

    def export_secrets(self, *, to: list[str], filterspec: str = '*:*:*',
                       serializer: str = 'json-crypt',
                       system: str | None = None) -> dict:
        """Encrypt matching secrets per recipient (cf. ``secrets:export``).
        """
        serializer_cls = SERIALIZERS.get(serializer)
        if serializer_cls is None:
            raise SeeqretError(f'unknown serializer: {serializer}')
        admin = self.storage.fetch_admin()
        fspec = FilterSpec(filterspec or '*:*:*')
        secrets = self.storage.fetch_secrets(**fspec.to_filterdict())
        private = vault_private_key()

        results = []
        for name in resolve_recipients(self.storage, to):
            receiver = admin if name == 'self' \
                else resolve_user(self.storage, name)
            s = serializer_cls(
                sender=admin, receiver=receiver,
                sender_private_key=private,
            )
            output = s.dumps(secrets, system or sys.platform)
            results.append(dict(
                username=receiver.username,
                email=receiver.email,
                output=output,
                count=len(secrets),
            ))
        return dict(count=len(secrets), results=results)

    def matching_secrets(self, filterspec: str) -> list[dict]:
        """Preview helper: which secrets a filter would export.
        """
        return self.list_secrets(filterspec or '*:*:*')

    # ---- secrets:import (two-phase merge) ------------------------------

    def import_preview(self, *, content: str,
                       from_user: str | None = None,
                       serializer: str = 'json-crypt') -> dict:
        """Phase 1: classify the payload against the vault.

           Returns jseeqret's phase-1 shape; the plan is parked on
           the facade for ``import_apply``.
        """
        serializer_cls = SERIALIZERS.get(serializer)
        if serializer_cls is None:
            raise SeeqretError(f'unknown serializer: {serializer}')

        sender_name = from_user
        if not sender_name and serializer == 'json-crypt':
            sender_name = JsonCryptSerializer.sender_username(content)
        if not sender_name:
            raise SeeqretError('no sender given (and none in payload)')
        sender = resolve_user(self.storage, sender_name)

        s = serializer_cls(
            sender=sender,
            receiver=self.storage.fetch_admin(),
            receiver_private_key=vault_private_key(),
        )
        incoming = s.load(content)
        plan = merge.plan_secret_merge(self.storage, incoming)
        self._pending_merge = plan
        return dict(
            needs_resolution=bool(plan['conflicts']),
            additions=len(plan['additions']),
            identical=len(plan['identical']),
            conflicts=merge.conflict_summary(plan),
        )

    def import_apply(self, resolutions: dict | None = None) -> dict:
        """Phase 2: apply the parked plan under explicit resolutions.
        """
        if self._pending_merge is None:
            raise SeeqretError('no pending import (run preview first)')
        result = merge.apply_secret_merge(
            self.storage, self._pending_merge, resolutions or {})
        self._pending_merge = None
        return result

    # ---- vaults:* -------------------------------------------------------

    def list_vaults(self) -> list[dict]:
        """Registered vaults, marking the active one.
        """
        active = get_seeqret_dir() if 'SEEQRET' in os.environ else None
        vaults = []
        for entry in vault_registry.registry_list():
            entry = dict(entry)
            entry['initialized'] = os.path.exists(
                os.path.join(entry['path'], 'seeqrets.db'))
            entry['active'] = (
                active and Path(entry['path']) == Path(active))
            vaults.append(entry)
        return vaults

    def switch_vault(self, name: str) -> str:
        """Make a registered vault active (and the registry default).
        """
        path = vault_registry.registry_resolve(name)
        if not path:
            raise SeeqretError(f'unregistered vault: {name}')
        vault_registry.registry_use(name)
        os.environ['SEEQRET'] = path
        self.storage = SqliteStorage()
        self._pending_merge = None
        return path

    def register_vault(self, name: str, path: str) -> None:
        vault_registry.registry_add(name, path)

    def unregister_vault(self, name: str) -> None:
        vault_registry.registry_remove(name)

    def create_vault(self, parent_dir: str, email: str,
                     name: str | None = None) -> dict:
        """Create a vault at ``<parent_dir>/seeqret``, register it,
           and switch to it (cf. ``vaults:create``).

           Core init chatter (click.echo) is captured and returned
           as ``log`` for display.
        """
        parent = Path(parent_dir).resolve()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            secrets_init(parent, qualified_user(), email)
        vault_dir = str(parent / 'seeqret')
        reg_name = name or parent.name
        vault_registry.registry_add(reg_name, vault_dir)
        vault_registry.registry_use(reg_name)
        os.environ['SEEQRET'] = vault_dir
        self.storage = SqliteStorage()
        return dict(name=reg_name, path=vault_dir, log=buf.getvalue())

    # ---- slack:* ----------------------------------------------------------

    def slack_status(self) -> dict:
        """Login/channel/preflight summary (cf. ``slack:status`` +
           ``slack:doctor``'s ready flag).
        """
        status = slack_session_status(self.storage)
        snap = status['snap']
        token_age = mfa_age = None
        if snap.get('token_created_at'):
            token_age = int(
                (time.time() - snap['token_created_at']) / 86400)
        if snap.get('mfa_attested_at'):
            mfa_age = int(
                (time.time() - snap['mfa_attested_at']) / 86400)
        return dict(
            ready=status['ready'],
            problems=status['problems'],
            logged_in=bool(snap.get('user_token')),
            team_name=snap.get('team_name'),
            user_id=snap.get('user_id'),
            channel_name=snap.get('channel_name'),
            channel_id=snap.get('channel_id'),
            token_age_days=token_age,
            mfa_age_days=mfa_age,
        )

    def slack_login(self) -> list[dict]:
        """Run the OAuth flow (blocking -- call from a worker
           thread), store the session, and return the private
           channels for the channel picker.
        """
        import webbrowser
        from ..slack.client import SlackClient
        from ..slack.oauth import run_oauth_flow

        auth = run_oauth_flow(open_browser=webbrowser.open)
        keys = slack_config.SLACK_KEYS
        slack_config.slack_config_set(
            self.storage, keys['user_token'], auth['access_token'])
        slack_config.slack_config_set(
            self.storage, keys['team_id'], auth.get('team_id'))
        slack_config.slack_config_set(
            self.storage, keys['team_name'], auth.get('team_name'))
        slack_config.slack_config_set(
            self.storage, keys['user_id'], auth.get('user_id'))
        slack_config.slack_config_set(
            self.storage, keys['token_created_at'], int(time.time()))
        return SlackClient(auth['access_token']).list_private_channels()

    def slack_set_channel(self, channel_id: str,
                          channel_name: str) -> None:
        keys = slack_config.SLACK_KEYS
        slack_config.slack_config_set(
            self.storage, keys['channel_id'], channel_id)
        slack_config.slack_config_set(
            self.storage, keys['channel_name'], channel_name)

    def slack_logout(self) -> None:
        slack_config.slack_config_clear_all(self.storage)

    def slack_attest_mfa(self) -> None:
        """Record the operator's SSO+MFA attestation (cf. ``slack:attest``).
        """
        slack_config.slack_config_set(
            self.storage, slack_config.SLACK_KEYS['mfa_attested_at'],
            int(time.time()))

    def slack_selftest(self) -> dict:
        return transport_selftest(slack_ctx(self.storage))

    def send_secrets_slack(self, *, to: list[str],
                           filterspec: str = '*:*:*') -> list[dict]:
        """Send json-crypt exports over Slack (cf. ``secrets:send-slack``).
        """
        ctx = slack_ctx(self.storage)
        export = self.export_secrets(
            to=to, filterspec=filterspec, serializer='json-crypt')
        results = []
        for rec in export['results']:
            try:
                require_verified_binding(self.storage, rec['username'])
                slack_user = ctx['client'].lookup_user_by_email(
                    rec['email'])
                if slack_user is None:
                    raise SeeqretError(
                        f"no Slack user for email {rec['email']!r}")
                sent = send_blob(
                    client=ctx['client'],
                    channel_id=ctx['channel_id'],
                    recipient_slack_user_id=slack_user['id'],
                    ciphertext=rec['output'],
                )
                results.append(dict(username=rec['username'], ok=True,
                                    count=rec['count'],
                                    file_id=sent['file_id']))
            except Exception as e:
                results.append(dict(username=rec['username'], ok=False,
                                    error=str(e)))
        return results

    # ---- onboard:* ----------------------------------------------------

    def onboard_invite(self, email: str, project: str | None,
                       name: str | None) -> dict:
        return onboarding.onboard_invite(
            self.storage, slack_ctx(self.storage),
            email=email, project=project, name=name)

    def onboard_list(self) -> list[dict]:
        onboarding.expire_stale_onboarding(self.storage)
        return self.storage.onboarding_list()

    def onboard_poll(self) -> list[dict]:
        return onboarding.onboard_poll(
            self.storage, slack_ctx(self.storage))

    def onboard_approve(self, email: str, verified: bool,
                        fingerprint_input: str) -> dict:
        return onboarding.onboard_approve(
            self.storage, slack_ctx(self.storage),
            email=email, verified=verified,
            fingerprint_input=fingerprint_input)

    def onboard_inbox(self) -> list[dict]:
        return onboarding.inbox_introductions(
            self.storage, slack_ctx(self.storage))

    def onboard_accept(self, pending: dict, verified: bool = False,
                       fingerprint_input: str = '') -> int:
        return onboarding.accept_introduction(
            self.storage, slack_ctx(self.storage),
            payload=pending['payload'],
            file_id=pending['file_id'],
            reply_ts=pending['reply_ts'],
            verified=verified,
            fingerprint_input=fingerprint_input)

    # ---- vault:introduction --------------------------------------------

    def introduction(self) -> dict | None:
        """The current user's shareable identity (cf. ``vault:introduction``).

           Returns None when the current user is not registered in
           the vault.
        """
        user = self.storage.fetch_user(qualified_user())
        if not user:
            return None
        cmd = (f'seeqret add user --username {user.username} '
               f'--email {user.email} --pubkey {user.pubkey}')
        if user.name:
            cmd += f' --name "{user.name}"'
        return dict(
            username=user.username,
            name=user.name,
            email=user.email,
            pubkey=user.pubkey,
            fingerprint=fingerprint(user.pubkey.encode('utf-8')),
            add_command=cmd,
        )
