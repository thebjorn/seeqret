import base64
import json

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from seeqret.serializers.self_decrypting_html import (
    encrypt_payload, to_self_decrypting_html,
)


def _browser_decrypt(env, password):
    """Mirror the embedded viewer's Web Crypto decrypt path exactly."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32,
        salt=base64.b64decode(env['salt']), iterations=env['iter'],
    )
    key = kdf.derive(password.encode('utf-8'))
    pt = AESGCM(key).decrypt(
        base64.b64decode(env['iv']), base64.b64decode(env['ct']), None)
    return pt.decode('utf-8')


def test_round_trip():
    env = encrypt_payload('hello secrets', 'hunter2')
    assert env['cipher'] == 'AES-256-GCM'
    assert env['kdf'] == 'PBKDF2-SHA256'
    assert _browser_decrypt(env, 'hunter2') == 'hello secrets'


def test_wrong_password_fails():
    env = encrypt_payload('hello secrets', 'hunter2')
    with pytest.raises(InvalidTag):
        _browser_decrypt(env, 'wrong-password')


def test_no_plaintext_in_envelope():
    env = encrypt_payload('super-secret-value', 'pw')
    assert 'super-secret-value' not in json.dumps(env)


def test_fresh_salt_and_iv_each_call():
    a = encrypt_payload('x', 'pw')
    b = encrypt_payload('x', 'pw')
    assert a['salt'] != b['salt']
    assert a['iv'] != b['iv']
    assert a['ct'] != b['ct']


def test_html_embeds_envelope_and_viewer():
    html = to_self_decrypting_html('{"secrets": []}', 'pw')
    assert 'id="vault"' in html
    assert 'crypto.subtle' in html
    assert 'AES-GCM' in html
    # the envelope embedded in the page decrypts back
    start = html.index('id="vault"')
    body = html[html.index('>', start) + 1:]
    env = json.loads(body[:body.index('</script>')])
    assert _browser_decrypt(env, 'pw') == '{"secrets": []}'
