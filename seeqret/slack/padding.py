"""Size-bucket padding for Slack-exchange ciphertext blobs.

   Why: Slack exposes file sizes to every channel member. An unpadded
   ciphertext leaks the number of secrets per export and supports
   correlation attacks (security-concerns.md #2). Padding to a fixed
   bucket defeats that.

   Format (big-endian):
       [4-byte length prefix] [payload bytes] [random tail up to bucket]

   The 4-byte prefix holds the real payload length. The receiver uses
   it to strip the random tail before passing the ciphertext on.

   The bucket size and length-prefix layout MUST match jseeqret's
   src/core/slack/padding.js byte-for-byte so blobs travel between the
   two CLIs.
"""

import os
import struct

DEFAULT_BUCKET = 4096


def pad_to_bucket(payload: bytes, bucket: int = DEFAULT_BUCKET) -> bytes:
    """Pad *payload* up to the next multiple of *bucket* bytes.

       The final blob is exactly ``N * bucket`` bytes long, including
       the 4-byte length prefix.
    """
    prefix_len = 4
    total_len = prefix_len + len(payload)
    # Round up to the next bucket boundary.
    padded_total = ((total_len + bucket - 1) // bucket) * bucket
    pad_len = padded_total - total_len

    prefix = struct.pack('>I', len(payload))
    pad_bytes = os.urandom(pad_len) if pad_len > 0 else b''
    return prefix + payload + pad_bytes


def unpad_from_bucket(padded: bytes) -> bytes:
    """Strip the length prefix and random padding from a padded blob.
    """
    if len(padded) < 4:
        raise ValueError(
            'padded blob is shorter than the length prefix'
        )

    payload_len = struct.unpack('>I', padded[:4])[0]
    if payload_len < 0 or payload_len > len(padded) - 4:
        raise ValueError(
            f'padded blob claims payload_len={payload_len}'
            f' but only {len(padded) - 4} bytes follow the prefix'
        )

    return padded[4:4 + payload_len]
