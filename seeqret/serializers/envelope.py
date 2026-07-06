"""Typed message envelope for the Slack transport (mirrors jseeqret).

   Every blob moved over Slack is a JSON envelope
   ``{"v": 1, "kind": <kind>, "payload": <object>}`` so receivers can
   route onboarding traffic without trial-decrypting. Legacy blobs
   (bare json-crypt payloads from before the envelope existed) parse
   as kind ``secret``.
"""
import json

ENVELOPE_VERSION = 1

MESSAGE_KINDS = (
    'secret',
    'invite',
    'introduction',
    'user_list',
    'secret_batch',
    'complete',
    'received',
    'selftest',
)


def wrap_envelope(kind: str, payload) -> str:
    """Serialize *payload* under a typed envelope.
    """
    if kind not in MESSAGE_KINDS:
        raise ValueError(f'unknown envelope kind: {kind}')
    return json.dumps({'v': ENVELOPE_VERSION, 'kind': kind,
                       'payload': payload})


def parse_envelope(text: str | bytes) -> dict:
    """Parse an inbound blob into ``{kind, payload, version}``.

       A blob that is not a typed envelope is treated as a legacy
       bare secret payload (kind ``secret``, version ``None``).
    """
    if isinstance(text, bytes):
        text = text.decode('utf-8')
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {'kind': 'secret', 'payload': text, 'version': None}

    if (isinstance(data, dict)
            and isinstance(data.get('kind'), str)
            and 'payload' in data):
        return {
            'kind': data['kind'],
            'payload': data['payload'],
            'version': data.get('v'),
        }
    return {'kind': 'secret', 'payload': data, 'version': None}
