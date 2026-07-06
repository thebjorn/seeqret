"""End-to-end Slack transport selftest (mirrors jseeqret's
   selftest.js).

   Sends a ``selftest`` envelope (a random nonce -- never secrets)
   addressed to yourself, then polls it back through the real
   receive pipeline, asserting the thread/mention structure works.
   The message is deleted afterwards (own message, so the delete
   must succeed).
"""
import uuid

from ..serializers.envelope import parse_envelope, wrap_envelope
from .transport import delete_thread, poll_inbox, send_blob


def transport_selftest(ctx: dict) -> dict:
    """Run the loopback test on an asserted-ready ``slack_ctx``.

       Returns ``{ok, sent, matched, deleted, error}``.
    """
    result = dict(ok=False, sent=False, matched=False, deleted=False,
                  error=None)
    nonce = uuid.uuid4().hex
    try:
        sent = send_blob(
            client=ctx['client'],
            channel_id=ctx['channel_id'],
            recipient_slack_user_id=ctx['self_user_id'],
            ciphertext=wrap_envelope('selftest', dict(nonce=nonce)),
        )
        result['sent'] = True

        oldest = str(float(sent['file_ts']) - 1)
        match = None
        for msg in poll_inbox(
            client=ctx['client'],
            channel_id=ctx['channel_id'],
            self_user_id=ctx['self_user_id'],
            oldest_ts=oldest,
        ):
            env = parse_envelope(msg['ciphertext'])
            if (env['kind'] == 'selftest'
                    and env['payload'].get('nonce') == nonce):
                match = msg
                break
        if match is None:
            result['error'] = 'sent selftest blob did not come back'
            return result
        result['matched'] = True

        delete_thread(
            client=ctx['client'],
            channel_id=ctx['channel_id'],
            file_id=match['file_id'],
            reply_ts=match['reply_ts'],
        )
        result['deleted'] = True
        result['ok'] = True
    except Exception as e:
        result['error'] = str(e)
    return result
