"""Thin wrapper around slack_sdk.WebClient.

Everything seeqret needs from Slack fits in ~10 methods. The
``WebClient`` already handles 429 backoff (``RateLimitedError``), so
this wrapper is mostly a vocabulary layer:

  - keeps all Slack calls in one place so auditing is easy
  - normalizes return shapes to plain dicts
  - hides the difference between files_upload_v2, files_delete,
    etc. behind one ``SlackClient`` surface
  - takes the token by injection (no globals) so the caller can
    pull it from the vault kv on every command invocation

Concern #8 (rate limits / availability): the WebClient's default
retry policy does exponential backoff. Our fail-closed behavior
lives in transport.py.
"""

from __future__ import annotations

from typing import Iterable

import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackClient:
    def __init__(self, token: str):
        if not token:
            raise ValueError('SlackClient: missing OAuth token')
        self.token = token
        self.web = WebClient(token=token)

    # ---- auth / workspace ----

    def auth_test(self) -> dict:
        r = self.web.auth_test()
        return {
            'ok': r['ok'],
            'team_id': r.get('team_id'),
            'team_name': r.get('team'),
            'user_id': r.get('user_id'),
            'user_name': r.get('user'),
            'url': r.get('url'),
        }

    def list_private_channels(self) -> list[dict]:
        r = self.web.conversations_list(
            types='private_channel',
            exclude_archived=True,
            limit=200,
        )
        return [
            {'id': c['id'], 'name': c['name']}
            for c in r.get('channels', [])
            if c.get('is_member')
        ]

    def lookup_user_by_email(self, email: str) -> dict | None:
        try:
            r = self.web.users_lookupByEmail(email=email)
        except SlackApiError as e:
            if e.response.get('error') == 'users_not_found':
                return None
            raise
        u = r.get('user')
        if not u:
            return None
        return {
            'id': u['id'],
            'name': u.get('name'),
            'real_name': u.get('real_name'),
        }

    def users_info(self, user_id: str) -> dict:
        r = self.web.users_info(user=user_id)
        return dict(r['user'])

    # ---- file upload / download ----

    def upload_blob(self, *, channel_id: str, filename: str,
                    content_bytes: bytes) -> dict:
        """Upload a binary blob as a file-share message to a channel.
        Returns ``{file_id, channel_id, ts}``.
        """
        r = self.web.files_upload_v2(
            channel=channel_id,
            filename=filename,
            content=content_bytes,
            # Empty title: do not leak secret-count or app:env:key
            # information through the upload metadata.
            title='',
        )
        # files_upload_v2 returns different shapes depending on SDK
        # version. Try the common paths.
        files = r.get('files') or []
        first = files[0] if files else r.get('file')
        if first is None:
            raise RuntimeError('files_upload_v2 returned no file info')

        ts = None
        shares = first.get('shares', {})
        priv = shares.get('private', {}).get(channel_id)
        if priv:
            ts = priv[0].get('ts')
        if ts is None and first.get('timestamp'):
            ts = str(first['timestamp'])

        return {
            'file_id': first.get('id'),
            'channel_id': channel_id,
            'ts': ts,
        }

    def file_info(self, file_id: str) -> dict:
        r = self.web.files_info(file=file_id)
        f = r.get('file')
        if f is None:
            raise RuntimeError(f'files.info returned no file for {file_id}')
        return {
            'id': f['id'],
            'url_private': f.get('url_private'),
            'size': f.get('size'),
            'name': f.get('name'),
        }

    def download_file(self, url_private: str) -> bytes:
        """Authenticated download of a Slack private file.

        slack_sdk does not wrap this: Slack expects an
        ``Authorization: Bearer <token>`` header against
        ``url_private``. Requests is already a dependency of the
        project.
        """
        res = requests.get(
            url_private,
            headers={'Authorization': f'Bearer {self.token}'},
            timeout=30,
        )
        if not res.ok:
            raise RuntimeError(
                f'slack file download failed:'
                f' {res.status_code} {res.reason}'
            )
        return res.content

    def delete_file(self, file_id: str) -> None:
        self.web.files_delete(file=file_id)

    # ---- messaging ----

    def post_thread_reply(self, *, channel_id: str, thread_ts: str,
                          text: str) -> dict:
        r = self.web.chat_postMessage(
            channel=channel_id, thread_ts=thread_ts, text=text,
        )
        return {'ts': r['ts']}

    def delete_message(self, *, channel_id: str, ts: str) -> None:
        self.web.chat_delete(channel=channel_id, ts=ts)

    def conversations_history(self, *, channel_id: str,
                              oldest_ts: str = '0',
                              limit: int = 100) -> list[dict]:
        r = self.web.conversations_history(
            channel=channel_id,
            oldest=oldest_ts,
            inclusive=False,
            limit=limit,
        )
        # Slack returns newest-first; reverse so callers process in
        # chronological order.
        return list(reversed(r.get('messages', [])))

    def conversations_replies(self, *, channel_id: str,
                              ts: str) -> list[dict]:
        r = self.web.conversations_replies(channel=channel_id, ts=ts)
        return list(r.get('messages', []))

    # ---- connected-apps audit (for slack doctor) ----

    def list_connected_apps(self) -> list[dict]:
        """Enumerate workspace connected apps for the doctor baseline.

        Slack's API for this varies by workspace tier. We try a couple
        of endpoints and return whatever we get. ``slack doctor``
        hashes the result; absence is treated as a warning rather than
        a silent pass.
        """
        try:
            # Not available on every workspace.
            r = self.web.api_call('apps.connections.list')
            if r.get('ok'):
                return list(r.get('connections', []))
        except SlackApiError:
            pass
        return []
