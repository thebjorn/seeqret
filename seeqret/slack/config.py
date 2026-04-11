"""Fernet-wrapped Slack configuration store.

   All Slack tokens and channel metadata live in the vault's ``kv``
   table (migration v003). Values are JSON-serialized, Fernet-encrypted
   with the vault's symmetric key, and written as BLOB.

   This implements security-concerns.md #3: the Slack user token gets
   the same at-rest protection as every other secret in the vault and
   never touches disk in plaintext.
"""

import json
import os

from cryptography.fernet import Fernet

from ..run_utils import get_seeqret_dir
from ..seeqrypt.utils import load_symetric_key


SLACK_KV_PREFIX = 'slack.'

SLACK_KEYS = {
    'user_token':          'slack.user_token',
    'team_id':             'slack.team_id',
    'team_name':           'slack.team_name',
    'user_id':             'slack.user_id',
    'channel_id':          'slack.channel_id',
    'channel_name':        'slack.channel_name',
    'last_seen_ts':        'slack.last_seen_ts',
    'connected_apps_hash': 'slack.connected_apps_hash',
    'token_created_at':    'slack.token_created_at',
    'mfa_attested_at':     'slack.mfa_attested_at',
}


def _fernet() -> Fernet:
    """Load the vault's Fernet symmetric key.

       Raises FileNotFoundError if the vault has not been initialized.
    """
    vault = get_seeqret_dir()
    return load_symetric_key(os.path.join(vault, 'seeqret.key'))


def slack_config_get(storage, key: str):
    """Fetch and decrypt a Slack config value.

       Returns None if no row with *key* exists.
    """
    blob = storage.kv_get(key)
    if blob is None:
        return None
    plaintext = _fernet().decrypt(bytes(blob))
    return json.loads(plaintext.decode('utf-8'))


def slack_config_set(storage, key: str, value) -> None:
    """Fernet-encrypt *value* (JSON-serializable) and upsert it.
    """
    plaintext = json.dumps(value).encode('utf-8')
    token = _fernet().encrypt(plaintext)
    storage.kv_set(key, token)


def slack_config_delete(storage, key: str) -> None:
    """Delete a single Slack config row.
    """
    storage.kv_delete(key)


def slack_config_clear_all(storage) -> None:
    """Wipe every ``slack.*`` kv entry.

       Used by ``seeqret slack logout`` to drop the full Slack session
       state in a single call.
    """
    storage.kv_delete_prefix(SLACK_KV_PREFIX)


def slack_config_snapshot(storage) -> dict:
    """Return every known Slack config key as a dict.

       Missing entries are returned as None. Convenience helper for
       ``slack status`` and ``slack doctor``.
    """
    out = {}
    for name, key in SLACK_KEYS.items():
        out[name] = slack_config_get(storage, key)
    return out
