"""Slack transport for NaCl-encrypted export blobs.

This module is purely about moving bytes across Slack. It does NOT
encrypt or decrypt -- that is still the job of the existing export
serializer. The transport only:

  send_blob         -- pads ciphertext, uploads as a file, posts a
                       recipient mention in the file's thread
  poll_inbox        -- generator walking history forward, yielding
                       dicts for messages that mention self_user_id
  delete_thread     -- files.delete + chat.delete after a successful
                       import, honoring forward secrecy

Fail-closed semantics (security-concerns.md #6, #8): on any Slack
error the caller must NOT advance ``last_seen_ts`` and must exit
non-zero. This module raises; ``receive`` catches and reports.
"""

from __future__ import annotations

import uuid
from typing import Iterator

from .client import SlackClient
from .padding import pad_to_bucket, unpad_from_bucket


def send_blob(*, client: SlackClient, channel_id: str,
              recipient_slack_user_id: str,
              ciphertext: bytes | str) -> dict:
    """Upload a ciphertext blob and post a recipient mention.

    Returns ``{file_id, file_ts, reply_ts}``.
    """
    if isinstance(ciphertext, str):
        payload = ciphertext.encode('utf-8')
    else:
        payload = bytes(ciphertext)

    padded = pad_to_bucket(payload)
    filename = f'jsenc-{uuid.uuid4()}.bin'

    upload = client.upload_blob(
        channel_id=channel_id,
        filename=filename,
        content_bytes=padded,
    )

    if not upload.get('ts'):
        # Cannot post a thread reply without the file-share ts. Fail
        # closed and clean up the orphaned file so we do not leak a
        # naked ciphertext into the channel without a recipient.
        try:
            client.delete_file(upload['file_id'])
        except Exception:
            pass
        raise RuntimeError(
            'slack upload did not return a file-share timestamp;'
            ' aborting to avoid posting ciphertext without a recipient'
        )

    # Concern #2: the thread body is ONLY the mention. No filename,
    # no app:env:key path, no commentary.
    reply = client.post_thread_reply(
        channel_id=channel_id,
        thread_ts=upload['ts'],
        text=f'<@{recipient_slack_user_id}>',
    )

    return {
        'file_id': upload['file_id'],
        'file_ts': upload['ts'],
        'reply_ts': reply['ts'],
    }


def poll_inbox(*, client: SlackClient, channel_id: str,
               self_user_id: str,
               oldest_ts: str = '0') -> Iterator[dict]:
    """Yield each inbound blob addressed to me since *oldest_ts*.

    A message is "addressed to me" when its thread contains a reply
    whose text is exactly ``<@SELF_USER_ID>``.

    Each yielded dict has: ``file_ts``, ``reply_ts``, ``file_id``,
    ``sender_user_id``, ``ciphertext`` (bytes, already unpadded).
    """
    messages = client.conversations_history(
        channel_id=channel_id,
        oldest_ts=oldest_ts,
    )

    self_mention = f'<@{self_user_id}>'

    for msg in messages:
        files = msg.get('files') or []
        if not files:
            continue

        blob_file = next(
            (f for f in files if (f.get('name') or '').startswith('jsenc-')),
            None,
        )
        if blob_file is None:
            continue

        thread = client.conversations_replies(
            channel_id=channel_id,
            ts=msg['ts'],
        )
        mention = next(
            (m for m in thread
             if m.get('ts') != msg.get('ts')
             and (m.get('text') or '').strip() == self_mention),
            None,
        )
        if mention is None:
            continue

        info = client.file_info(blob_file['id'])
        raw = client.download_file(info['url_private'])
        ciphertext = unpad_from_bucket(raw)

        yield {
            'file_ts': msg['ts'],
            'reply_ts': mention['ts'],
            'file_id': blob_file['id'],
            'sender_user_id': msg.get('user'),
            'ciphertext': ciphertext,
        }


def delete_thread(*, client: SlackClient, channel_id: str,
                  file_id: str, reply_ts: str) -> None:
    """Delete both the uploaded file and the thread mention after a
    successful import. Failure is fatal: the caller must NOT advance
    ``last_seen_ts`` or the same blob will be re-imported forever.
    """
    client.delete_message(channel_id=channel_id, ts=reply_ts)
    client.delete_file(file_id)
