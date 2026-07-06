"""Slack transport session assembly + preflight (mirrors
   jseeqret's session.js).

   Every send/receive/onboarding call funnels through ``slack_ctx``,
   which refuses to hand out a client unless the doctor-level
   preflight passes: logged in, channel set, token fresh, MFA
   attested.
"""
import time

from ..errors import SeeqretError
from .client import SlackClient
from .config import slack_config_snapshot


def slack_preflight_problems(snap: dict) -> list[str]:
    """The minimum ``slack doctor`` checks enforced before any
       transport use. An empty list means ready.
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
            problems.append(f'MFA attestation is {age_days} days old (>90)')

    return problems


def slack_session_status(storage) -> dict:
    """``{ready, problems, snap}`` without raising.
    """
    snap = slack_config_snapshot(storage)
    problems = slack_preflight_problems(snap)
    return dict(ready=not problems, problems=problems, snap=snap)


def slack_ctx(storage) -> dict:
    """An asserted-ready transport context.

       Returns ``{client, channel_id, self_user_id, snap}``; raises
       SeeqretError listing the preflight problems otherwise.
    """
    snap = slack_config_snapshot(storage)
    problems = slack_preflight_problems(snap)
    if problems:
        raise SeeqretError(
            'Slack transport not ready: ' + '; '.join(problems))
    return dict(
        client=SlackClient(snap['user_token']),
        channel_id=snap['channel_id'],
        self_user_id=snap['user_id'],
        snap=snap,
    )
