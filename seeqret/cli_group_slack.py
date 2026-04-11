"""Click command group for `seeqret slack ...` and the send/receive
dispatchers.

This file is a thin CLI layer around seeqret/slack/*. All
security-sensitive logic (fingerprint verification, Fernet wrapping,
delete-on-import, doctor checks) lives in the core modules.
"""

import hashlib
import json
import sys
import time
import webbrowser

import click

from .filterspec import FilterSpec
from .models import Secret
from .run_utils import seeqret_dir
from .seeqrypt.nacl_backend import load_private_key
from .serializers.serializer import SERIALIZERS
from .storage.sqlite_storage import SqliteStorage

from .slack.client import SlackClient
from .slack.config import (
    SLACK_KEYS,
    slack_config_clear_all,
    slack_config_get,
    slack_config_set,
    slack_config_snapshot,
)
from .slack.identity import (
    bind_slack_handle,
    compute_fingerprint,
    find_user_by_slack_handle,
    require_verified_binding,
)
from .slack.oauth import run_oauth_flow
from .slack.transport import delete_thread, poll_inbox, send_blob


# ---- helpers ----------------------------------------------------------

def _load_client(storage) -> SlackClient:
    token = slack_config_get(storage, SLACK_KEYS['user_token'])
    if not token:
        raise click.ClickException(
            'Not logged in to Slack. Run: seeqret slack login'
        )
    return SlackClient(token)


def _preflight_slack_cfg(snap) -> list[str]:
    """Minimum set of doctor checks `send` enforces before dialing Slack.
    """
    problems = []
    if not snap.get('user_token'):
        problems.append('not logged in (seeqret slack login)')
    if not snap.get('channel_id'):
        problems.append('no channel set')

    token_created_at = snap.get('token_created_at')
    if token_created_at:
        age_days = int((time.time() - token_created_at) / 86400)
        if age_days > 90:
            problems.append(f'token is {age_days} days old (>90)')

    mfa_attested_at = snap.get('mfa_attested_at')
    if not mfa_attested_at:
        problems.append('MFA not attested (seeqret slack doctor --accept)')
    else:
        age_days = int((time.time() - mfa_attested_at) / 86400)
        if age_days > 90:
            problems.append(
                f'MFA attestation is {age_days} days old (>90)'
            )

    return problems


# ---- slack group ------------------------------------------------------

@click.group('slack')
def slack():
    """Slack-based secret exchange transport."""
    pass


@slack.command('login')
def slack_login():
    """OAuth login to Slack and pick an exchange channel.
    """
    with seeqret_dir():
        storage = SqliteStorage()

        click.echo('Starting Slack OAuth flow...')

        def _open(url):
            click.echo(f'Opening browser: {url}')
            try:
                webbrowser.open(url)
            except Exception:
                click.echo('Open this URL manually: ' + url)

        auth = run_oauth_flow(open_browser=_open)

        slack_config_set(storage, SLACK_KEYS['user_token'], auth['access_token'])
        slack_config_set(storage, SLACK_KEYS['team_id'], auth.get('team_id'))
        slack_config_set(storage, SLACK_KEYS['team_name'], auth.get('team_name'))
        slack_config_set(storage, SLACK_KEYS['user_id'], auth.get('user_id'))
        slack_config_set(
            storage,
            SLACK_KEYS['token_created_at'],
            int(time.time()),
        )

        click.echo(
            f"Authenticated as <@{auth.get('user_id')}>"
            f" in {auth.get('team_name')}."
        )

        client = SlackClient(auth['access_token'])
        who = client.auth_test()
        click.echo(f"auth.test -> {who['user_name']} ({who['team_name']})")

        channels = client.list_private_channels()
        if not channels:
            raise click.ClickException(
                'No private channels found for this user.'
                ' Create #seeqrets and invite yourself, then re-run.'
            )

        click.echo('\nPrivate channels:')
        for i, c in enumerate(channels):
            click.echo(f"  [{i + 1}] #{c['name']}")

        default_idx = next(
            (i for i, c in enumerate(channels) if c['name'] == 'seeqrets'),
            0,
        ) + 1
        pick = click.prompt(
            f'\nPick the exchange channel [1-{len(channels)}]',
            default=default_idx,
            type=int,
        )
        if pick < 1 or pick > len(channels):
            raise click.ClickException('Invalid selection.')
        chosen = channels[pick - 1]

        slack_config_set(storage, SLACK_KEYS['channel_id'], chosen['id'])
        slack_config_set(storage, SLACK_KEYS['channel_name'], chosen['name'])

        click.echo(
            f"\nOK. Exchange channel set to #{chosen['name']} ({chosen['id']})."
        )
        click.echo('Next: run `seeqret slack doctor --accept` before sending.')


@slack.command('logout')
def slack_logout():
    """Wipe all Slack configuration from the vault."""
    with seeqret_dir():
        storage = SqliteStorage()
        slack_config_clear_all(storage)
        click.echo('Slack configuration cleared.')


@slack.command('status')
def slack_status():
    """Show Slack login / channel / last-seen state."""
    with seeqret_dir():
        storage = SqliteStorage()
        snap = slack_config_snapshot(storage)

        if not snap.get('user_token'):
            click.echo('Not logged in. Run: seeqret slack login')
            return

        token_age = None
        if snap.get('token_created_at'):
            token_age = int(
                (time.time() - snap['token_created_at']) / 86400
            )

        click.echo(
            f"team:         {snap.get('team_name') or '?'}"
            f" ({snap.get('team_id') or '?'})"
        )
        click.echo(f"user_id:      {snap.get('user_id') or '?'}")
        click.echo(
            f"channel:      #{snap.get('channel_name') or '?'}"
            f" ({snap.get('channel_id') or '?'})"
        )
        click.echo(
            f"last_seen_ts: {snap.get('last_seen_ts') or '(none)'}"
        )
        click.echo(
            f"token age:    "
            f"{str(token_age) + ' days' if token_age is not None else '(unknown)'}"
        )


@slack.command('link')
@click.argument('username')
@click.option('--handle', default=None,
              help='Slack handle without the @ (defaults to username)')
def slack_link(username, handle):
    """Bind a local user to a Slack handle after fingerprint confirmation.
    """
    with seeqret_dir():
        storage = SqliteStorage()
        local = storage.fetch_user(username)
        if not local:
            raise click.ClickException(
                f"local user '{username}' not found."
            )

        fp = compute_fingerprint(local)
        handle = handle or username

        click.echo(f'\nLocal user: {username} <{local.email}>')
        click.echo(f'Slack handle: @{handle}')
        click.echo(f'Public key fingerprint: {fp}')
        click.echo(
            '\nConfirm OUT-OF-BAND (voice, in-person, not via Slack) that'
            ' the fingerprint above matches what the other party sees'
            ' locally in their vault.'
        )

        answer = click.prompt(
            f'Type "{fp}" to confirm you have verified this fingerprint',
            default='',
            show_default=False,
        )
        if answer.strip() != fp:
            raise click.ClickException(
                'Fingerprint confirmation mismatch. Refusing to bind.'
            )

        bind_slack_handle(storage, username, handle)
        click.echo(f'Bound {username} -> @{handle} (fingerprint {fp}).')


@slack.command('doctor')
@click.option('--accept', is_flag=True, default=False,
              help='Re-baseline connected-apps and MFA attestation')
def slack_doctor(accept):
    """Preflight health check for the Slack exchange transport.
    """
    with seeqret_dir():
        storage = SqliteStorage()
        snap = slack_config_snapshot(storage)

        results = []

        def _check(label, ok, detail=''):
            results.append((label, ok, detail))

        _check(
            'logged in',
            bool(snap.get('user_token')),
            f"as user {snap.get('user_id')}" if snap.get('user_token')
            else 'run: seeqret slack login',
        )

        token_age_days = None
        if snap.get('token_created_at'):
            token_age_days = int(
                (time.time() - snap['token_created_at']) / 86400
            )
        _check(
            'token age <= 90 days',
            token_age_days is not None and token_age_days <= 90,
            (f'{token_age_days} days old' if token_age_days is not None
             else 'no token_created_at stamp'),
        )

        _check(
            'channel configured',
            bool(snap.get('channel_id')),
            f"#{snap.get('channel_name')}" if snap.get('channel_id')
            else 'run: seeqret slack login',
        )

        users = storage.fetch_users()
        linked = [u for u in users if u.slack_handle]
        now = time.time()

        def _stale(u):
            if not u.slack_verified_at:
                return True
            return (now - u.slack_verified_at) / 86400 > 180

        stale = [u for u in linked if _stale(u)]
        _check(
            'linked users verified in last 180 days',
            len(linked) > 0 and not stale,
            ('no linked users' if not linked
             else f"{len(linked)} linked, all fresh" if not stale
             else f"stale: {', '.join(u.username for u in stale)}"),
        )

        drifted = [
            u for u in linked
            if compute_fingerprint(u) != u.slack_key_fingerprint
        ]
        _check(
            'stored fingerprints match current pubkeys',
            not drifted,
            'ok' if not drifted
            else f"drift: {', '.join(u.username for u in drifted)}",
        )

        mfa_age_days = None
        if snap.get('mfa_attested_at'):
            mfa_age_days = int(
                (time.time() - snap['mfa_attested_at']) / 86400
            )
        _check(
            'workspace SSO + hardware MFA attested (<= 90 days)',
            mfa_age_days is not None and mfa_age_days <= 90,
            (f'{mfa_age_days} days old' if mfa_age_days is not None
             else 're-run with --accept to attest'),
        )

        # Connected-apps baseline.
        if snap.get('user_token'):
            try:
                client = SlackClient(snap['user_token'])
                apps = client.list_connected_apps()
                h = hashlib.sha256(
                    json.dumps(
                        sorted(a.get('id') or a.get('name', '') for a in apps)
                    ).encode('utf-8')
                ).hexdigest()
                if not snap.get('connected_apps_hash'):
                    _check(
                        'connected-apps baseline', False,
                        'no baseline (run --accept to set)',
                    )
                elif snap['connected_apps_hash'] == h:
                    _check('connected-apps unchanged', True, 'unchanged')
                else:
                    _check(
                        'connected-apps unchanged', False,
                        'CHANGED since last baseline',
                    )
                if accept:
                    slack_config_set(
                        storage, SLACK_KEYS['connected_apps_hash'], h,
                    )
            except Exception as e:
                _check(
                    'connected-apps unchanged', False, f'error: {e}',
                )

        if accept:
            if click.confirm(
                'Confirm workspace enforces SSO + hardware MFA',
                default=False,
            ):
                slack_config_set(
                    storage, SLACK_KEYS['mfa_attested_at'], int(time.time()),
                )
                click.echo('MFA attestation recorded.')
            else:
                click.echo('MFA attestation NOT recorded.')

        all_ok = True
        for label, ok, detail in results:
            mark = click.style('[ok]  ', fg='green') if ok \
                else click.style('[FAIL]', fg='red')
            suffix = f' -- {detail}' if detail else ''
            click.echo(f'{mark} {label}{suffix}')
            if not ok:
                all_ok = False

        if not all_ok:
            raise click.ClickException(
                'slack doctor: one or more checks failed.'
            )
        click.echo('\nslack doctor: all checks passed.')


# ---- send / receive ---------------------------------------------------

@click.command('send')
@click.argument('filters', nargs=-1)
@click.option('--to', required=True, help='Recipient username in the local vault')
@click.option('--via', default='file', show_default=True,
              help='Transport: file or slack')
@click.option('-o', '--out', default=None,
              help='Output file path (file transport only)')
@click.pass_context
def send(ctx, filters, to, via, out):
    """Send encrypted secrets to a user via file or Slack."""
    with seeqret_dir():
        storage = SqliteStorage()

        recipient = storage.fetch_user(to)
        if recipient is None:
            raise click.ClickException(
                f"user '{to}' not found in vault."
            )

        # Build the ciphertext (same pipeline as `seeqret export`).
        admin = storage.fetch_admin()
        serializer_cls = SERIALIZERS.get('json-crypt')

        sender_private = load_private_key('private.key')
        serializer = serializer_cls(
            sender=admin,
            receiver=recipient,
            sender_private_key=sender_private,
        )

        all_secrets = []
        fspecs = filters or ('*:*:*',)
        for f in fspecs:
            fspec = FilterSpec(f)
            all_secrets.extend(storage.fetch_secrets(**fspec.to_filterdict()))

        if not all_secrets:
            raise click.ClickException('No matching secrets found.')

        ciphertext = serializer.dumps(all_secrets, sys.platform)

        if via == 'file':
            if out:
                with open(out, 'w') as f:
                    f.write(ciphertext)
                click.echo(
                    f'Exported {len(all_secrets)} secret(s) to {out} for {to}'
                )
            else:
                click.echo(ciphertext)
            return

        if via != 'slack':
            raise click.ClickException(f"unknown transport '{via}'")

        # --- slack path ---
        require_verified_binding(storage, to)

        snap = slack_config_snapshot(storage)
        problems = _preflight_slack_cfg(snap)
        if problems:
            click.echo('Slack transport not ready:', err=True)
            for p in problems:
                click.echo(f'  - {p}', err=True)
            click.echo('Run: seeqret slack doctor', err=True)
            ctx.exit(1)

        client = SlackClient(snap['user_token'])
        slack_user = client.lookup_user_by_email(recipient.email)
        if slack_user is None:
            raise click.ClickException(
                f"cannot resolve Slack user by email '{recipient.email}'."
                ' Make sure the recipient is in this workspace.'
            )

        result = send_blob(
            client=client,
            channel_id=snap['channel_id'],
            recipient_slack_user_id=slack_user['id'],
            ciphertext=ciphertext,
        )
        click.echo(
            f"Sent {len(all_secrets)} secret(s) to {to} via Slack"
            f" (file {result['file_id']}, ts {result['file_ts']})."
        )


@click.command('receive')
@click.option('--via', default='slack', show_default=True,
              help='Transport: slack')
@click.option('--watch', is_flag=True, default=False,
              help='Poll continuously until interrupted')
@click.option('--interval', default=30, show_default=True,
              type=int, help='Poll interval in seconds (with --watch)')
@click.pass_context
def receive(ctx, via, watch, interval):
    """Receive and import encrypted secrets from a transport."""
    if via != 'slack':
        raise click.ClickException(f"unknown transport '{via}'")

    with seeqret_dir():
        storage = SqliteStorage()
        snap = slack_config_snapshot(storage)
        if not (snap.get('user_token')
                and snap.get('channel_id')
                and snap.get('user_id')):
            raise click.ClickException(
                'Slack transport not configured. Run: seeqret slack login'
            )

        def _run_once():
            client = SlackClient(snap['user_token'])
            receiver_private = load_private_key('private.key')
            serializer_cls = SERIALIZERS.get('json-crypt')

            oldest_ts = snap.get('last_seen_ts') or '0'
            imported = 0
            highest_ts = oldest_ts

            for msg in poll_inbox(
                client=client,
                channel_id=snap['channel_id'],
                self_user_id=snap['user_id'],
                oldest_ts=oldest_ts,
            ):
                slack_user = client.users_info(msg['sender_user_id'])
                sender = find_user_by_slack_handle(
                    storage, slack_user.get('name'),
                )
                if sender is None:
                    raise click.ClickException(
                        "inbound blob from unknown Slack handle"
                        f" '@{slack_user.get('name')}' (user_id"
                        f" {msg['sender_user_id']}). Run:"
                        f" seeqret slack link <local_user>"
                        f" --handle {slack_user.get('name')}"
                    )

                serializer = serializer_cls(
                    sender=sender,
                    receiver=storage.fetch_admin(),
                    receiver_private_key=receiver_private,
                )
                text = msg['ciphertext'].decode('utf-8')
                secrets = serializer.load(text)
                for secret in secrets:
                    storage.add_secret(secret)
                    imported += 1

                delete_thread(
                    client=client,
                    channel_id=snap['channel_id'],
                    file_id=msg['file_id'],
                    reply_ts=msg['reply_ts'],
                )

                if msg['file_ts'] > highest_ts:
                    highest_ts = msg['file_ts']

            if highest_ts != oldest_ts:
                slack_config_set(
                    storage, SLACK_KEYS['last_seen_ts'], highest_ts,
                )
            return imported

        try:
            n = _run_once()
            if n > 0:
                click.echo(f'Imported {n} secret(s) from Slack.')
        except click.ClickException:
            raise
        except Exception as e:
            raise click.ClickException(f'receive failed: {e}')

        if watch:
            click.echo(
                f'Watching Slack every {interval}s (Ctrl-C to stop).'
            )
            while True:
                time.sleep(interval)
                # Re-read the config so a concurrent `slack login`
                # rotation is picked up without a restart.
                snap.update(slack_config_snapshot(storage))
                try:
                    n = _run_once()
                    if n > 0:
                        click.echo(
                            f'Imported {n} secret(s) from Slack.'
                        )
                except Exception as e:
                    click.echo(f'receive failed: {e}', err=True)
