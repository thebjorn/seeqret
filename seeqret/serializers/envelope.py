"""Typed message envelope for the Slack exchange transport.

   Mirrors jseeqret's ``src/core/serializers/envelope.js`` so both
   tools can share the exchange channel. A secret blob is a bare JSON
   object (``{version, from, to, secrets, signature}``) with no type
   tag; jseeqret's onboarding adds several typed message kinds that
   travel over the same pipe, wrapped in a thin ``{v, kind, payload}``
   envelope. The encryption boundary is unchanged: the payload's
   sensitive fields are still NaCl-encrypted by the relevant
   serializer; the envelope itself is plaintext structure.

   Backward compatibility: a blob with no ``kind`` is a legacy secret
   export, so ``parse_envelope`` reports it as kind ``secret`` with
   the whole object as the payload.
"""

import json

ENVELOPE_VERSION = 1

#: The message kinds that travel over the exchange channel. Only
#: ``secret`` is produced/consumed by seeqret; the rest are jseeqret
#: onboarding traffic that ``receive`` must recognize and leave alone.
MESSAGE_KINDS = {
    'secret': 'secret',
    'invite': 'invite',
    'introduction': 'introduction',
    'user_list': 'user_list',
    'secret_batch': 'secret_batch',
    'complete': 'complete',
    'received': 'received',
    'selftest': 'selftest',
}


def wrap_envelope(kind: str, payload) -> str:
    """Wrap a kind-specific payload in a typed envelope.
    """
    return json.dumps({
        'v': ENVELOPE_VERSION,
        'kind': kind,
        'payload': payload,
    })


def parse_envelope(text: str) -> dict:
    """Parse an envelope. A blob without a ``kind``/``payload`` pair
       is treated as a legacy secret export (the whole object is the
       payload). Raises ``ValueError`` (``json.JSONDecodeError``) for
       text that is not JSON at all.
    """
    data = json.loads(text)

    if (isinstance(data, dict)
            and isinstance(data.get('kind'), str)
            and 'payload' in data):
        return {
            'kind': data['kind'],
            'payload': data['payload'],
            'version': data.get('v'),
        }

    return {
        'kind': MESSAGE_KINDS['secret'],
        'payload': data,
        'version': None,
    }
