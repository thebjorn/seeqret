"""Slack handle to NaCl public key binding.

   Implements security-concerns.md #4: a Slack handle is NEVER trusted
   as a source of public-key material. Before seeqret will send
   ciphertext to ``@bob`` via Slack, the operator must have run
   ``seeqret slack link bob`` and typed back the 5-character
   fingerprint of bob's public key (out-of-band verification).

   The fingerprint is cached in the users table. Any later mismatch --
   for example if the users row is rewritten by an attacker or the key
   is rotated without a fresh ``slack link`` -- causes ``send`` to
   refuse.
"""

import time

from ..models import User
from ..seeqrypt.nacl_backend import fingerprint as nacl_fingerprint


def compute_fingerprint(user: User) -> str:
    """Return the 5-character fingerprint of a user's public key.

       The hash is taken over the raw 32-byte public key bytes (not
       the base64 string), which matches jseeqret's
       ``compute_fingerprint``.
    """
    return nacl_fingerprint(bytes(user.public_key))


def bind_slack_handle(storage, username: str, slack_handle: str):
    """Record a slack handle binding after out-of-band confirmation.

       Callers are responsible for displaying the fingerprint and
       collecting the confirmation. This function only persists the
       result, so it is safe to unit-test in isolation.
    """
    user = storage.fetch_user(username)
    if user is None:
        raise ValueError(f'Unknown local user: {username}')

    fp = compute_fingerprint(user)
    now = int(time.time())
    storage.update_user_slack(
        username,
        slack_handle=slack_handle,
        slack_key_fingerprint=fp,
        slack_verified_at=now,
    )
    return user, fp


def require_verified_binding(storage, username: str):
    """Return a ``(user, slack_handle)`` pair for a verified binding.

       Raises ValueError if the binding is missing or stale. Used by
       ``send`` to refuse to push ciphertext via Slack if the binding
       has drifted since the last ``slack link``.
    """
    user = storage.fetch_user(username)
    if user is None:
        raise ValueError(f'Unknown local user: {username}')
    if not user.slack_handle:
        raise ValueError(
            f"User '{username}' is not linked to a Slack handle."
            f' Run: seeqret slack link {username}'
        )
    if not user.slack_key_fingerprint:
        raise ValueError(
            f"User '{username}' has no stored Slack fingerprint."
            f' Re-run: seeqret slack link {username}'
        )

    current = compute_fingerprint(user)
    if current != user.slack_key_fingerprint:
        raise ValueError(
            f"Refusing to send to '{username}' via Slack:"
            f' stored fingerprint {user.slack_key_fingerprint}'
            f' no longer matches current pubkey fingerprint {current}.'
            f' Re-verify out-of-band and re-run:'
            f' seeqret slack link {username}'
        )

    return user, user.slack_handle


def find_user_by_slack_handle(storage, slack_handle: str):
    """Return the local user with the given *slack_handle*, or None.

       Used by ``receive`` to resolve an inbound sender. Slack
       identity alone does not authenticate the ciphertext -- NaCl Box
       does -- but we still need to know *which* local pubkey to
       decrypt against.
    """
    for user in storage.fetch_users():
        if user.slack_handle == slack_handle:
            return user
    return None
