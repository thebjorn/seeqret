"""OAuth v2 PKCE loopback flow for ``seeqret slack login``.

   Flow:
     1. Generate a PKCE code verifier and challenge.
     2. Bind a one-shot http server on ``127.0.0.1:<ephemeral>``.
     3. Open the user's browser at ``slack.com/oauth/v2/authorize``
        with a redirect_uri pointing at our loopback port.
     4. Wait for Slack to redirect back with ``?code=...``.
     5. Exchange the code and verifier for a user token via
        ``oauth.v2.access``.
     6. Shut down the server and return the token.

   The Client ID is baked into seeqret (see ``SLACK_CLIENT_ID``
   below).
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import os
import secrets
import threading
import webbrowser
from urllib.parse import urlencode, urlparse, parse_qs

from slack_sdk import WebClient


# SLACK_CLIENT_ID is a placeholder. The real maintainer should set
# the env var or replace the default string before releasing a build
# with the Client ID of the published seeqret Slack app.
SLACK_CLIENT_ID = os.environ.get(
    'SEEQRET_SLACK_CLIENT_ID',
    '0000000000.0000000000000',
)

SLACK_USER_SCOPES = ','.join([
    'channels:history',
    'channels:read',
    'groups:history',
    'groups:read',
    'files:read',
    'files:write',
    'chat:write',
    'users:read',
    'users:read.email',
])


def _url_safe_random(n_bytes: int) -> str:
    """Return a URL-safe base64 string of *n_bytes* random bytes.
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(n_bytes))\
        .rstrip(b'=').decode('ascii')


def _pkce_pair() -> tuple[str, str]:
    """Return a fresh ``(verifier, challenge)`` pair for PKCE S256.
    """
    verifier = _url_safe_random(32)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode('ascii')).digest()
    ).rstrip(b'=').decode('ascii')
    return verifier, challenge


class _CallbackServer(http.server.HTTPServer):
    """One-shot loopback HTTP server for the OAuth redirect.

       Stores the received ``code`` (or ``error``) on the instance
       and signals ``_done`` so the main thread can wake up and
       exchange the code for a token.
    """

    allow_reuse_address = False

    def __init__(self, address, expected_state):
        super().__init__(address, _CallbackHandler)
        self.expected_state = expected_state
        self.code: str | None = None
        self.error: str | None = None
        self._done = threading.Event()

    def wait(self, timeout: float) -> None:
        """Block until the callback has been handled or *timeout*.
        """
        self._done.wait(timeout)


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for the one-shot ``/callback`` endpoint.
    """

    def log_message(self, format, *args):
        """Silence the default request log.

           The user is watching the CLI, not this server.
        """
        return

    def do_GET(self):
        """Handle the single ``GET /callback?...`` redirect.
        """
        server: _CallbackServer = self.server  # type: ignore
        parsed = urlparse(self.path)
        if parsed.path != '/callback':
            self.send_response(404)
            self.end_headers()
            return

        qs = parse_qs(parsed.query)
        got_state = (qs.get('state') or [None])[0]
        got_code = (qs.get('code') or [None])[0]
        got_error = (qs.get('error') or [None])[0]

        if got_error:
            server.error = f'slack oauth error: {got_error}'
            self._html(400, '<h1>Slack login failed</h1>')
        elif got_state != server.expected_state:
            server.error = 'slack oauth: state mismatch'
            self._html(400, '<h1>Invalid state</h1>')
        elif not got_code:
            server.error = 'slack oauth: missing code'
            self._html(400, '<h1>Missing code</h1>')
        else:
            server.code = got_code
            self._html(
                200,
                '<h1>Success</h1><p>You can close this tab and return'
                ' to the terminal.</p>',
            )

        server._done.set()

    def _html(self, status: int, body: str) -> None:
        """Write an HTML response of *status* with *body*.
        """
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write((
            '<!doctype html><meta charset="utf-8">'
            '<title>seeqret slack login</title>' + body
        ).encode('utf-8'))


def run_oauth_flow(open_browser=None, timeout_seconds: int = 180) -> dict:
    """Run the PKCE loopback flow to completion.

       Returns a dict with ``access_token``, ``team_id``,
       ``team_name`` and ``user_id``. Raises ``RuntimeError`` if the
       browser handshake fails, times out, or Slack rejects the code.

       *open_browser* is an optional callable that receives the
       authorize URL; defaults to ``webbrowser.open``.
    """
    verifier, challenge = _pkce_pair()
    state = _url_safe_random(24)

    server = _CallbackServer(('127.0.0.1', 0), state)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    redirect_uri = f'http://127.0.0.1:{port}/callback'
    params = {
        'client_id': SLACK_CLIENT_ID,
        'user_scope': SLACK_USER_SCOPES,
        'redirect_uri': redirect_uri,
        'state': state,
        'code_challenge': challenge,
        'code_challenge_method': 'S256',
    }
    authorize_url = 'https://slack.com/oauth/v2/authorize?' + urlencode(params)

    try:
        if open_browser is not None:
            open_browser(authorize_url)
        else:
            try:
                webbrowser.open(authorize_url)
            except Exception:
                print('Open this URL in your browser:\n  ' + authorize_url)

        server.wait(timeout_seconds)

        if server.error:
            raise RuntimeError(server.error)
        if server.code is None:
            raise RuntimeError('slack login timed out')

        web = WebClient()
        r = web.oauth_v2_access(
            client_id=SLACK_CLIENT_ID,
            code=server.code,
            redirect_uri=redirect_uri,
            code_verifier=verifier,
        )
        if not r.get('ok'):
            raise RuntimeError(
                f'slack oauth.v2.access failed: {r.get("error")}'
            )

        authed_user = r.get('authed_user') or {}
        access_token = authed_user.get('access_token') or r.get('access_token')
        if not access_token:
            raise RuntimeError('slack oauth: no user access_token in response')

        return {
            'access_token': access_token,
            'team_id': (r.get('team') or {}).get('id'),
            'team_name': (r.get('team') or {}).get('name'),
            'user_id': authed_user.get('id'),
        }
    finally:
        server.shutdown()
        server.server_close()
