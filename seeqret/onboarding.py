"""Slack-based team onboarding state machine (mirrors jseeqret's
   onboarding.js).

   Two roles exchange typed envelopes over the shared exchange
   channel:

   Team lead (TL):  invite -> poll (capture introduction) ->
                    approve (send user_list + secret_batch +
                    complete) -> receive ``received`` ack
   New user:        receive-invite -> introduce/join ->
                    provision-poll (import user_list/secret_batch,
                    verify complete proof, ack)

   Authentication model: the 5-char fingerprint is display-only OOB
   verification UX; the real trust anchor is the full 32-byte TL
   public key captured at ``join`` time. All imports authenticate by
   NaCl-Box-decrypting against that anchored key (``pubkeys_equal``
   is constant-time).

   Divergence from jseeqret: the poll cursor only advances to the
   highest *handled* message ts -- the stale-noise fast-forward
   (``STALE_AFTER_SECONDS``) is not ported yet, so unrelated old
   channel messages are re-scanned (correct, just less efficient).
"""
import base64
import hmac
import json
import os
import time

from .errors import SeeqretError
from .filterspec import FilterSpec
from .models import User
from .run_utils import get_seeqret_dir
from .seeqrypt.nacl_backend import (
    asymetric_decrypt_string,
    asymetric_encrypt_string,
    fingerprint,
    load_private_key,
    public_key,
)
from .serializers import JsonCryptSerializer, UserListSerializer
from .serializers.envelope import parse_envelope, wrap_envelope
from .slack.config import SLACK_KEYS, slack_config_get, slack_config_set
from .slack.identity import compute_fingerprint
from .slack.transport import delete_thread, poll_inbox, send_blob

ONBOARDING_STATES = (
    'invited', 'introduced', 'approved', 'provisioned', 'complete',
    'expired',
)
STATE_ORDER = ONBOARDING_STATES[:5]
RESENDABLE_STATES = ('invited', 'complete', 'expired')
DEFAULT_INVITE_TTL_SECONDS = 7 * 86400

COMPLETE_PROOF = 'jseeqret-onboard-complete'
RECEIVED_PROOF = 'jseeqret-onboard-received'
DEFAULT_DOWNLOAD_URL = \
    'https://github.com/thebjorn/jseeqret/releases/latest'

ONBOARD_KEYS = {
    'tl_user_id':     'onboard.tl_user_id',
    'tl_pubkey':      'onboard.tl_pubkey',
    'tl_fingerprint': 'onboard.tl_fingerprint',
    'project':        'onboard.project',
    'wizard':         'onboard.wizard',
    'introduced':     'onboard.introduced',
    'received_ack':   'onboard.received_ack',
}


def pubkey_fingerprint(pubkey_b64: str) -> str:
    """5-char fingerprint over the raw 32-byte public key.
    """
    return fingerprint(base64.b64decode(pubkey_b64))


def pubkeys_equal(a: str | None, b: str | None) -> bool:
    """Constant-time comparison of two base64 public keys.
    """
    if not a or not b:
        return False
    try:
        return hmac.compare_digest(base64.b64decode(a),
                                   base64.b64decode(b))
    except (ValueError, TypeError):
        return False


def _self_private_key():
    return load_private_key(
        os.path.join(get_seeqret_dir(), 'private.key'))


def _fetch_self(storage):
    admin = storage.fetch_admin()
    if admin is None:
        raise SeeqretError('vault has no owner')
    return admin


# ---- trust context (new-user side) -----------------------------------

def set_tl_trust(storage, *, tl_user_id, tl_pubkey, tl_fingerprint,
                 project=None) -> None:
    """Anchor the team lead's identity after OOB verification.
    """
    slack_config_set(storage, ONBOARD_KEYS['tl_user_id'], tl_user_id)
    slack_config_set(storage, ONBOARD_KEYS['tl_pubkey'], tl_pubkey)
    slack_config_set(storage, ONBOARD_KEYS['tl_fingerprint'],
                     tl_fingerprint)
    if project is not None:
        slack_config_set(storage, ONBOARD_KEYS['project'], project)


def get_tl_trust(storage) -> dict:
    return dict(
        tl_user_id=slack_config_get(storage, ONBOARD_KEYS['tl_user_id']),
        tl_pubkey=slack_config_get(storage, ONBOARD_KEYS['tl_pubkey']),
        tl_fingerprint=slack_config_get(
            storage, ONBOARD_KEYS['tl_fingerprint']),
        project=slack_config_get(storage, ONBOARD_KEYS['project']),
    )


def trust_status(storage) -> dict:
    """Cheap local probe used by the wizard (cf. onboard:trust-status).
    """
    trust = get_tl_trust(storage)
    return dict(has_trust=bool(trust['tl_pubkey']))


def wizard_active(storage) -> bool:
    return slack_config_get(storage, ONBOARD_KEYS['wizard']) == 'active'


def set_wizard_active(storage, active: bool) -> None:
    slack_config_set(storage, ONBOARD_KEYS['wizard'],
                     'active' if active else '')


# ---- envelope traffic --------------------------------------------------

def poll_envelopes(ctx: dict, oldest_ts: str = '0'):
    """Yield typed envelopes addressed to me since *oldest_ts*.
    """
    for msg in poll_inbox(
        client=ctx['client'],
        channel_id=ctx['channel_id'],
        self_user_id=ctx['self_user_id'],
        oldest_ts=oldest_ts,
    ):
        env = parse_envelope(msg['ciphertext'])
        env.update(
            sender_user_id=msg['sender_user_id'],
            file_id=msg['file_id'],
            file_ts=msg['file_ts'],
            reply_ts=msg['reply_ts'],
        )
        yield env


def _send_envelope(ctx: dict, recipient_slack_user_id: str,
                   kind: str, payload) -> dict:
    return send_blob(
        client=ctx['client'],
        channel_id=ctx['channel_id'],
        recipient_slack_user_id=recipient_slack_user_id,
        ciphertext=wrap_envelope(kind, payload),
    )


def _record_sent(storage, email: str, sent: dict) -> None:
    """Track envelopes sent to a new user so the ``received`` ack can
       clean them up (TL-side forward secrecy).
    """
    key = f'onboard.sent.{email}'
    existing = slack_config_get(storage, key) or []
    existing.append(dict(file_id=sent['file_id'],
                         reply_ts=sent['reply_ts']))
    slack_config_set(storage, key, existing)


# ---- team-lead side ----------------------------------------------------

def expire_stale_onboarding(storage, now: int | None = None,
                            ttl: int = DEFAULT_INVITE_TTL_SECONDS) -> int:
    """Flip open invited/introduced rows older than *ttl* to expired.
    """
    now = now or int(time.time())
    expired = 0
    for row in storage.onboarding_list():
        if row['state'] in ('invited', 'introduced'):
            if now - (row['created_at'] or 0) > ttl:
                storage.onboarding_set_state(row['email'], 'expired')
                expired += 1
    return expired


def onboard_invite(storage, ctx: dict, *, email: str,
                   project: str | None = None,
                   name: str | None = None,
                   download_url: str = DEFAULT_DOWNLOAD_URL) -> dict:
    """Invite *email* to the team (cf. onboard:invite).
    """
    row = storage.onboarding_get(email)
    if row and row['state'] not in RESENDABLE_STATES:
        raise SeeqretError(
            f"onboarding for {email} is in state '{row['state']}'"
            ' -- wait for it to finish or expire')

    slack_user = ctx['client'].lookup_user_by_email(email)
    if slack_user is None:
        raise SeeqretError(
            f'no Slack user found for email {email!r}')

    self_user = _fetch_self(storage)
    storage.onboarding_create(dict(
        email=email,
        name=name,
        slack_user_id=slack_user['id'],
        project_filter=project,
        state='invited',
    ))

    payload = dict(
        email=email,
        project=project,
        download_url=download_url,
        tl_username=self_user.username,
        tl_email=self_user.email,
        tl_pubkey=self_user.pubkey,
        tl_fingerprint=compute_fingerprint(self_user),
    )
    _send_envelope(ctx, slack_user['id'], 'invite', payload)
    return dict(email=email, slack_user_id=slack_user['id'],
                state='invited')


def onboard_poll(storage, ctx: dict) -> list[dict]:
    """Process inbound introductions and received-acks (TL side).
    """
    oldest = slack_config_get(
        storage, SLACK_KEYS['onboard_last_seen_ts']) or '0'
    events = []
    highest = oldest

    for env in poll_envelopes(ctx, oldest):
        if env['kind'] == 'introduction':
            events.append(_handle_introduction(storage, ctx, env))
        elif env['kind'] == 'received':
            handled = _handle_received_ack(storage, ctx, env)
            if handled:
                events.append(handled)
        else:
            continue
        if env['file_ts'] > highest:
            highest = env['file_ts']

    if highest != oldest:
        slack_config_set(
            storage, SLACK_KEYS['onboard_last_seen_ts'], highest)
    return events


def _handle_introduction(storage, ctx: dict, env: dict) -> dict:
    payload = env['payload']
    email = payload.get('email')
    row = storage.onboarding_get(email) if email else None
    expected = bool(row and row['state'] in ('invited', 'introduced'))
    fp = pubkey_fingerprint(payload['pubkey'])

    if expected:
        storage.onboarding_update(email, dict(
            username=payload.get('username'),
            # the TL's invite name wins over the self-reported one
            name=row.get('name') or payload.get('name'),
            slack_user_id=env['sender_user_id'],
            pubkey=payload['pubkey'],
            fingerprint=fp,
            state='introduced',
        ))
        delete_thread(
            client=ctx['client'], channel_id=ctx['channel_id'],
            file_id=env['file_id'], reply_ts=env['reply_ts'])
    return dict(kind='introduction', email=email, fingerprint=fp,
                expected=expected)


def _handle_received_ack(storage, ctx: dict, env: dict) -> dict | None:
    payload = env['payload']
    email = payload.get('email')
    row = storage.onboarding_get(email) if email else None
    if not row or not row.get('pubkey'):
        return None
    try:
        proof = asymetric_decrypt_string(
            payload['proof'],
            _self_private_key(),
            public_key(row['pubkey']),
        )
    except Exception:
        return dict(kind='received', email=email, verified=False)
    if proof != RECEIVED_PROOF:
        return dict(kind='received', email=email, verified=False)

    # authenticated: clean up every envelope we sent to this user
    key = f'onboard.sent.{email}'
    for sent in slack_config_get(storage, key) or []:
        try:
            delete_thread(
                client=ctx['client'], channel_id=ctx['channel_id'],
                file_id=sent['file_id'], reply_ts=sent['reply_ts'])
        except Exception:
            pass  # already deleted is fine
    storage.kv_delete(key)
    delete_thread(
        client=ctx['client'], channel_id=ctx['channel_id'],
        file_id=env['file_id'], reply_ts=env['reply_ts'])
    return dict(kind='received', email=email, verified=True)


def onboard_approve(storage, ctx: dict, *, email: str,
                    verified: bool, fingerprint_input: str) -> dict:
    """Approve an introduced user after the OOB fingerprint ceremony
       (cf. onboard:approve). Resumable from introduced/approved/
       provisioned.
    """
    row = storage.onboarding_get(email)
    if not row:
        raise SeeqretError(f'no onboarding row for {email}')
    if row['state'] not in ('introduced', 'approved', 'provisioned'):
        raise SeeqretError(
            f"cannot approve from state '{row['state']}'")

    # The security gate: enforced here, not in the UI.
    if not verified:
        raise SeeqretError('fingerprint must be verified out-of-band')
    if fingerprint_input != row['fingerprint']:
        raise SeeqretError('fingerprint mismatch')

    self_user = _fetch_self(storage)
    private = _self_private_key()

    new_user = storage.fetch_user(row['username'])
    if new_user is None:
        new_user = User(row['username'], email, row['pubkey'],
                        name=row.get('name'))
        storage.add_user(new_user)
        new_user = storage.fetch_user(row['username'])
    storage.update_user_slack(
        row['username'],
        slack_handle=(row.get('slack_handle')
                      or (row.get('name') or row['username'])
                      .split('@')[0]),
        slack_key_fingerprint=row['fingerprint'],
        slack_verified_at=int(time.time()),
    )
    storage.onboarding_set_state(email, 'approved')

    # 1. teammates -> new user
    teammates = [u for u in storage.fetch_users()
                 if u.username != row['username']]
    users_payload = json.loads(UserListSerializer(
        sender=self_user, receiver=new_user,
        sender_private_key=private,
    ).dumps(teammates))
    users_payload['from_pubkey'] = self_user.pubkey
    sent = _send_envelope(ctx, row['slack_user_id'], 'user_list',
                          users_payload)
    _record_sent(storage, email, sent)
    storage.onboarding_set_state(email, 'provisioned')

    # 2. new user -> each existing teammate (so they can send back)
    broadcasts = 0
    for teammate in teammates:
        if teammate.username == self_user.username:
            continue
        slack_user = ctx['client'].lookup_user_by_email(teammate.email)
        if slack_user is None:
            continue
        payload = json.loads(UserListSerializer(
            sender=self_user, receiver=teammate,
            sender_private_key=private,
        ).dumps([new_user]))
        payload['from_pubkey'] = self_user.pubkey
        _send_envelope(ctx, slack_user['id'], 'user_list', payload)
        broadcasts += 1

    # 3. project secrets
    fspec = FilterSpec(row.get('project_filter') or '*:*:*')
    secrets = storage.fetch_secrets(**fspec.to_filterdict())
    batch = json.loads(JsonCryptSerializer(
        sender=self_user, receiver=new_user,
        sender_private_key=private,
    ).dumps(secrets, 'linux'))
    batch['from_pubkey'] = self_user.pubkey
    sent = _send_envelope(ctx, row['slack_user_id'], 'secret_batch',
                          batch)
    _record_sent(storage, email, sent)

    # 4. completion proof
    proof = asymetric_encrypt_string(
        COMPLETE_PROOF, private, new_user.public_key)
    sent = _send_envelope(ctx, row['slack_user_id'], 'complete', dict(
        email=email,
        from_pubkey=self_user.pubkey,
        status='complete',
        proof=proof,
    ))
    _record_sent(storage, email, sent)
    storage.onboarding_set_state(email, 'complete')

    return dict(email=email, users_sent=len(teammates),
                secrets_sent=len(secrets), broadcasts=broadcasts)


# ---- new-user side -----------------------------------------------------

def onboard_receive_invite(storage, ctx: dict) -> dict | None:
    """Find the latest invite addressed to me (cf.
       onboard:receive-invite). The returned tl_fingerprint is
       recomputed from tl_pubkey -- never trusted as self-reported.
    """
    latest = None
    for env in poll_envelopes(ctx, '0'):
        if env['kind'] != 'invite':
            continue
        payload = dict(env['payload'])
        payload['tl_fingerprint'] = pubkey_fingerprint(
            payload['tl_pubkey'])
        payload.update(
            tl_slack_user_id=env['sender_user_id'],
            file_id=env['file_id'],
            reply_ts=env['reply_ts'],
            file_ts=env['file_ts'],
        )
        latest = payload
    return latest


def onboard_join(storage, ctx: dict, invite: dict) -> dict:
    """Introduce myself to the TL and anchor trust (cf. onboard:join).

       Anchoring trust is the OOB gate: only call this after the
       operator has voice-verified the TL fingerprint.
    """
    result = onboard_introduce(storage, ctx, invite, force=True)
    set_tl_trust(
        storage,
        tl_user_id=invite['tl_slack_user_id'],
        tl_pubkey=invite['tl_pubkey'],
        tl_fingerprint=pubkey_fingerprint(invite['tl_pubkey']),
        project=invite.get('project'),
    )
    return result


def onboard_introduce(storage, ctx: dict, invite: dict,
                      force: bool = False) -> dict:
    """Send my introduction WITHOUT anchoring trust (the wizard
       auto-sends this on invite discovery). Idempotent per email.
    """
    marker = slack_config_get(storage, ONBOARD_KEYS['introduced'])
    if marker and marker.get('email') == invite['email'] and not force:
        return dict(email=invite['email'], sent=False)

    self_user = _fetch_self(storage)
    payload = dict(
        email=invite['email'],
        username=self_user.username,
        name=self_user.name,
        pubkey=self_user.pubkey,
        fingerprint=compute_fingerprint(self_user),
    )
    _send_envelope(ctx, invite['tl_slack_user_id'], 'introduction',
                   payload)
    slack_config_set(storage, ONBOARD_KEYS['introduced'],
                     dict(email=invite['email'], at=int(time.time())))
    return dict(email=invite['email'], sent=True)


def onboard_provision_poll(storage, ctx: dict) -> dict:
    """Import provisioning traffic from the trusted TL (cf.
       onboard:provision-poll). Fail-closed: the cursor only
       advances when a pass produced zero warnings.
    """
    trust = get_tl_trust(storage)
    if not trust['tl_pubkey']:
        raise SeeqretError(
            'no team-lead trust anchored yet (verify the invite'
            ' fingerprint first)')
    tl_pubkey = trust['tl_pubkey']
    private = _self_private_key()
    self_user = _fetch_self(storage)

    oldest = slack_config_get(
        storage, SLACK_KEYS['onboard_user_last_seen_ts']) or '0'
    warnings = []
    users_imported = 0
    secrets_imported = 0
    completed = False
    highest = oldest

    for env in poll_envelopes(ctx, oldest):
        try:
            if env['kind'] == 'user_list':
                users_imported += _import_user_list(
                    storage, env['payload'], tl_pubkey, private)
            elif env['kind'] == 'secret_batch':
                secrets_imported += _import_secret_batch(
                    storage, self_user, env['payload'], tl_pubkey,
                    private)
            elif env['kind'] == 'complete':
                _verify_complete(env['payload'], tl_pubkey, private)
                completed = True
            else:
                continue
        except Exception as e:
            warnings.append(f"{env['kind']}: {e}")
            continue
        try:
            delete_thread(
                client=ctx['client'], channel_id=ctx['channel_id'],
                file_id=env['file_id'], reply_ts=env['reply_ts'])
        except Exception:
            pass  # receivers usually can't delete TL messages
        if env['file_ts'] > highest:
            highest = env['file_ts']

    if not warnings and highest != oldest:
        slack_config_set(
            storage, SLACK_KEYS['onboard_user_last_seen_ts'], highest)
    if completed:
        onboard_send_received_ack(storage, ctx)
    return dict(
        users_imported=users_imported,
        secrets_imported=secrets_imported,
        complete=completed,
        warnings=warnings,
    )


def _sender_stub(pubkey_b64: str) -> User:
    """A minimal sender User carrying only the trusted pubkey, for
       decrypt-side serializer construction.
    """
    return User('_tl', '', pubkey_b64)


def _import_user_list(storage, payload: dict, tl_pubkey: str,
                      private) -> int:
    """Auth: decrypt with the OOB-verified TL pubkey (NOT the
       self-reported from_pubkey).
    """
    serializer = UserListSerializer(
        sender=_sender_stub(tl_pubkey),
        receiver_private_key=private,
    )
    records = serializer.load(payload)

    imported = 0
    now = int(time.time())
    for rec in records:
        if storage.fetch_user(rec['username']):
            continue
        storage.add_user(User(rec['username'], rec['email'],
                              rec['pubkey'], name=rec.get('name')))
        storage.update_user_slack(
            rec['username'],
            slack_handle=rec['username'].split('@')[0],
            slack_key_fingerprint=pubkey_fingerprint(rec['pubkey']),
            slack_verified_at=now,
        )
        imported += 1
    return imported


def _import_secret_batch(storage, self_user, payload: dict,
                         tl_pubkey: str, private) -> int:
    """Authoritative provisioning push: upsert, no merge.
    """
    serializer = JsonCryptSerializer(
        sender=_sender_stub(tl_pubkey),
        receiver=self_user,
        receiver_private_key=private,
    )
    secrets = serializer.load(json.dumps(payload))
    for secret in secrets:
        storage.upsert_secret(secret)
    return len(secrets)


def _verify_complete(payload: dict, tl_pubkey: str, private) -> None:
    proof = asymetric_decrypt_string(
        payload['proof'], private, public_key(tl_pubkey))
    if proof != COMPLETE_PROOF:
        raise SeeqretError('completion proof mismatch')


def onboard_send_received_ack(storage, ctx: dict) -> bool:
    """Ack completion back to the TL (idempotent).
    """
    marker = slack_config_get(storage, ONBOARD_KEYS['received_ack'])
    if marker:
        return False
    trust = get_tl_trust(storage)
    introduced = slack_config_get(storage, ONBOARD_KEYS['introduced'])
    email = (introduced or {}).get('email')
    proof = asymetric_encrypt_string(
        RECEIVED_PROOF, _self_private_key(),
        public_key(trust['tl_pubkey']))
    _send_envelope(ctx, trust['tl_user_id'], 'received',
                   dict(email=email, proof=proof))
    slack_config_set(storage, ONBOARD_KEYS['received_ack'],
                     dict(email=email, at=int(time.time())))
    return True


# ---- existing-teammate side (introduction inbox) ----------------------

def inbox_introductions(storage, ctx: dict) -> list[dict]:
    """Pending user_list envelopes addressed to me, decrypted for
       display but NOT imported (cf. onboard:inbox).
    """
    trust = get_tl_trust(storage)
    private = _self_private_key()
    pending = []
    for env in poll_envelopes(ctx, '0'):
        if env['kind'] != 'user_list':
            continue
        payload = env['payload']
        from_pubkey = payload.get('from_pubkey')
        if not from_pubkey:
            continue
        try:
            serializer = UserListSerializer(
                sender=_sender_stub(from_pubkey),
                receiver_private_key=private,
            )
            users = serializer.load(payload)
        except Exception:
            continue
        pending.append(dict(
            file_id=env['file_id'],
            reply_ts=env['reply_ts'],
            file_ts=env['file_ts'],
            sender_user_id=env['sender_user_id'],
            from_pubkey=from_pubkey,
            fingerprint=pubkey_fingerprint(from_pubkey),
            vouched=pubkeys_equal(from_pubkey, trust['tl_pubkey']),
            users=users,
            payload=payload,
        ))
    return pending


def accept_introduction(storage, ctx: dict, *, payload: dict,
                        file_id: str, reply_ts: str,
                        verified: bool = False,
                        fingerprint_input: str = '') -> int:
    """Import a pending introduction after the trust gate passes:
       vouched (sender key == anchored TL key) OR an explicit OOB
       fingerprint confirmation.
    """
    trust = get_tl_trust(storage)
    from_pubkey = payload.get('from_pubkey')
    vouched = pubkeys_equal(from_pubkey, trust['tl_pubkey'])
    if not vouched:
        if not (verified
                and fingerprint_input == pubkey_fingerprint(from_pubkey)):
            raise SeeqretError(
                'introduction is not vouched by the team lead --'
                ' verify the sender fingerprint out-of-band')

    private = _self_private_key()
    serializer = UserListSerializer(
        sender=_sender_stub(from_pubkey),
        receiver_private_key=private,
    )
    records = serializer.load(payload)

    imported = 0
    now = int(time.time())
    for rec in records:
        if storage.fetch_user(rec['username']):
            continue
        storage.add_user(User(rec['username'], rec['email'],
                              rec['pubkey'], name=rec.get('name')))
        storage.update_user_slack(
            rec['username'],
            slack_handle=rec['username'].split('@')[0],
            slack_key_fingerprint=pubkey_fingerprint(rec['pubkey']),
            slack_verified_at=now,
        )
        imported += 1
    try:
        delete_thread(client=ctx['client'],
                      channel_id=ctx['channel_id'],
                      file_id=file_id, reply_ts=reply_ts)
    except Exception:
        pass
    return imported
