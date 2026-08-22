"""Regression tests for the Slack PKCE desktop OAuth flow."""

from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen

import seeqret.slack.oauth as oauth


class _FakeWebClient:
    """Capture the OAuth exchange without contacting Slack."""

    exchange = None

    def oauth_v2_access(self, **kwargs):
        """Return a representative Slack user-token response."""
        type(self).exchange = kwargs
        return {
            'ok': True,
            'authed_user': {'id': 'U1', 'access_token': 'xoxp-test'},
            'team': {'id': 'T1', 'name': 'NorskTest'},
        }


def _complete_callback(authorize_url: str, **params) -> None:
    """Forward a simulated Slack response to the loopback listener."""
    query = parse_qs(urlparse(authorize_url).query)
    state = query['state'][0]
    port = state.split('-', 1)[0]
    callback_params = {'state': state, **params}
    callback_url = (
        f'http://127.0.0.1:{port}/callback?'
        f'{urlencode(callback_params)}'
    )
    with urlopen(callback_url) as response:
        assert response.status == 200


def test_oauth_uses_published_app_and_registered_redirect(monkeypatch):
    """The released defaults must produce a Slack-recognized authorize URL."""
    monkeypatch.setattr(oauth, 'WebClient', _FakeWebClient)
    captured = {}

    def open_browser(url):
        captured['url'] = url
        _complete_callback(url, code='temporary-code')

    result = oauth.run_oauth_flow(open_browser=open_browser)

    query = parse_qs(urlparse(captured['url']).query)
    assert oauth.SLACK_CLIENT_ID != '0000000000.0000000000000'
    assert query['client_id'] == [oauth.SLACK_CLIENT_ID]
    assert query['redirect_uri'] == [oauth.SLACK_REDIRECT_URL]
    assert query['code_challenge_method'] == ['S256']
    assert query['state'][0].split('-', 1)[0].isdigit()

    assert _FakeWebClient.exchange['code'] == 'temporary-code'
    assert _FakeWebClient.exchange['redirect_uri'] == oauth.SLACK_REDIRECT_URL
    assert _FakeWebClient.exchange['code_verifier']
    assert result['access_token'] == 'xoxp-test'
