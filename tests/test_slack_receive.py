"""Tests for `seeqret receive --via slack`.

   Covers the JsonCryptSerializer.load implementation, envelope
   parsing, and the receive flow end-to-end against an in-memory mock
   of the exchange channel (a port of jseeqret's tests/slack-mock.js).

   Regression: typed onboarding envelopes posted by jseeqret used to
   crash receive -- every frame was fed to the json-crypt serializer,
   which requires a `secrets` array.
"""

import json

import pytest
from click.testing import CliRunner
from nacl.public import PrivateKey
from nacl import encoding

import seeqret.cli_group_slack as cli_slack
from seeqret.cli_group_slack import receive
from seeqret.main import init
from seeqret.models import User
from seeqret.models.secret import Secret
from seeqret.run_utils import current_user, seeqret_dir
from seeqret.serializers.envelope import (
    MESSAGE_KINDS, parse_envelope, wrap_envelope,
)
from seeqret.serializers.jsoncrypt_serializer import JsonCryptSerializer
from seeqret.slack.config import SLACK_KEYS, slack_config_set
from seeqret.slack.identity import bind_slack_handle
from seeqret.slack.transport import send_blob
from seeqret.storage.sqlite_storage import SqliteStorage

CHANNEL = 'C_SEEQRETS'


# ---- in-memory slack mock ---------------------------------------------

class MockSlackWorkspace:
    """Shared message store; `client(user_id)` returns a
       SlackClient-shaped object bound to that user, implementing
       exactly the surface transport.py and receive call.
    """

    def __init__(self):
        self.messages = []      # {ts, user, files?, text?, thread_ts?}
        self.files = {}         # file_id -> {id, name, bytes, url_private}
        self._seq = 0

    def _next_id(self, prefix):
        self._seq += 1
        return f'{prefix}{self._seq}'

    def _next_ts(self):
        self._seq += 1
        return f'{1000 + self._seq}.000000'

    def client(self, user_id):
        return MockSlackClient(self, user_id)


class MockSlackClient:
    def __init__(self, workspace, user_id):
        self.ws = workspace
        self.user_id = user_id

    def users_info(self, user_id):
        return {'id': user_id, 'name': user_id}

    def upload_blob(self, *, channel_id, filename, content_bytes):
        file_id = self.ws._next_id('F')
        ts = self.ws._next_ts()
        self.ws.files[file_id] = {
            'id': file_id,
            'name': filename,
            'bytes': bytes(content_bytes),
            'url_private': f'mock://{file_id}',
        }
        self.ws.messages.append({
            'ts': ts,
            'user': self.user_id,
            'files': [{'id': file_id, 'name': filename}],
            'text': '',
        })
        return {'file_id': file_id, 'channel_id': channel_id, 'ts': ts}

    def post_thread_reply(self, *, channel_id, thread_ts, text):
        ts = self.ws._next_ts()
        self.ws.messages.append({
            'ts': ts, 'user': self.user_id,
            'text': text, 'thread_ts': thread_ts,
        })
        return {'ts': ts}

    def conversations_history(self, *, channel_id, oldest_ts='0'):
        return sorted(
            (m for m in self.ws.messages
             if not m.get('thread_ts') and m.get('files')
             and float(m['ts']) > float(oldest_ts)),
            key=lambda m: float(m['ts']),
        )

    def conversations_replies(self, *, channel_id, ts):
        parent = next(
            (m for m in self.ws.messages if m['ts'] == ts), None)
        replies = [m for m in self.ws.messages if m.get('thread_ts') == ts]
        return [m for m in [parent, *replies] if m is not None]

    def file_info(self, file_id):
        f = self.ws.files[file_id]
        return {'id': f['id'], 'url_private': f['url_private'],
                'size': len(f['bytes']), 'name': f['name']}

    def download_file(self, url_private):
        file_id = url_private.replace('mock://', '')
        return bytes(self.ws.files[file_id]['bytes'])

    def delete_file(self, file_id):
        self.ws.files.pop(file_id, None)
        self.ws.messages = [
            m for m in self.ws.messages
            if not (m.get('files') and m['files'][0]['id'] == file_id)
        ]

    def delete_message(self, *, channel_id, ts):
        self.ws.messages = [m for m in self.ws.messages if m['ts'] != ts]


# ---- helpers ----------------------------------------------------------

def _init_vault(runner):
    result = runner.invoke(init, [
        '.',
        '--user=' + current_user(),
        '--email=test@example.com',
    ])
    assert result.exit_code == 0, result.output


def _keypair():
    sk = PrivateKey.generate()
    pub_b64 = encoding.Base64Encoder.encode(bytes(sk.public_key)).decode('ascii')
    return sk, pub_b64


def _alice_sends(ws, alice_user, alice_sk, receiver, specs):
    """Alice exports `specs` for the vault admin and posts the blob."""
    ser = JsonCryptSerializer(
        sender=alice_user,
        receiver=receiver,
        sender_private_key=alice_sk,
    )
    secrets = [Secret(**spec) for spec in specs]
    return send_blob(
        client=ws.client('U_ALICE'),
        channel_id=CHANNEL,
        recipient_slack_user_id='U_BOB',
        ciphertext=ser.dumps(secrets, 'linux'),
    )


def _configure_slack(storage):
    slack_config_set(storage, SLACK_KEYS['user_token'], 'xoxp-mock')
    slack_config_set(storage, SLACK_KEYS['user_id'], 'U_BOB')
    slack_config_set(storage, SLACK_KEYS['channel_id'], CHANNEL)


# ---- envelope ---------------------------------------------------------

def test_parse_envelope_legacy_blob_is_kind_secret():
    blob = json.dumps({'version': 1, 'from': 'a', 'to': 'b',
                       'secrets': [], 'signature': 'zzzzz'})
    env = parse_envelope(blob)
    assert env['kind'] == MESSAGE_KINDS['secret']
    assert env['payload']['from'] == 'a'
    assert env['version'] is None


def test_parse_envelope_typed_roundtrip():
    text = wrap_envelope(MESSAGE_KINDS['user_list'], {'users': []})
    env = parse_envelope(text)
    assert env['kind'] == 'user_list'
    assert env['payload'] == {'users': []}
    assert env['version'] == 1


def test_parse_envelope_rejects_non_json():
    with pytest.raises(ValueError):
        parse_envelope('not json at all')


# ---- serializer load --------------------------------------------------

def test_jsoncrypt_load_roundtrip():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            admin = storage.fetch_admin()
            alice_sk, alice_pub = _keypair()
            alice = User('alice@host', 'alice@test.com', alice_pub)

            ser = JsonCryptSerializer(
                sender=alice, receiver=admin,
                sender_private_key=alice_sk,
            )
            text = ser.dumps([
                Secret(app='myapp', env='prod', key='DB_PASS',
                       plaintext_value='s3cret'),
            ], 'linux')

            from seeqret.seeqrypt.nacl_backend import load_private_key
            loader = JsonCryptSerializer(
                sender=alice, receiver=admin,
                receiver_private_key=load_private_key('private.key'),
            )
            secrets = loader.load(text)
            assert len(secrets) == 1
            assert secrets[0].app == 'myapp'
            assert secrets[0].key == 'DB_PASS'
            assert secrets[0].value == 's3cret'


# ---- receive end-to-end ----------------------------------------------

def _receive_setup(runner):
    """Init a vault wired to a mock workspace; returns the pieces."""
    _init_vault(runner)
    with seeqret_dir():
        storage = SqliteStorage()
        admin = storage.fetch_admin()
        alice_sk, alice_pub = _keypair()
        alice = User('alice@host', 'alice@test.com', alice_pub)
        storage.add_user(alice)
        bind_slack_handle(storage, 'alice@host', 'U_ALICE')
        _configure_slack(storage)
    ws = MockSlackWorkspace()
    return storage, admin, alice, alice_sk, ws


def test_receive_imports_blob_and_deletes_thread(monkeypatch):
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        storage, admin, alice, alice_sk, ws = _receive_setup(runner)
        monkeypatch.setattr(
            cli_slack, 'SlackClient', lambda token: ws.client('U_BOB'))

        with seeqret_dir():
            sent = _alice_sends(ws, alice, alice_sk, admin, [
                dict(app='myapp', env='prod', key='DB_PASS',
                     plaintext_value='s3cret'),
            ])

        result = runner.invoke(receive, ['--via', 'slack'])
        assert result.exit_code == 0, result.output
        assert 'Imported 1 secret(s)' in result.output

        with seeqret_dir():
            storage = SqliteStorage()
            rows = storage.fetch_secrets(app='myapp', env='prod',
                                         key='DB_PASS')
            assert len(rows) == 1
            assert rows[0].value == 's3cret'
        # Forward secrecy: file and mention are gone.
        assert sent['file_id'] not in ws.files
        assert ws.messages == []


def test_receive_skips_onboarding_envelopes(monkeypatch):
    """Regression: a typed jseeqret envelope in the channel must be
       skipped, not fed to the json-crypt serializer (crash) and not
       deleted (it belongs to the onboarding pollers)."""
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        storage, admin, alice, alice_sk, ws = _receive_setup(runner)
        monkeypatch.setattr(
            cli_slack, 'SlackClient', lambda token: ws.client('U_BOB'))

        # An onboarding envelope addressed to bob from an unlinked
        # sender, followed by a genuine secret blob.
        send_blob(
            client=ws.client('U_TL'),
            channel_id=CHANNEL,
            recipient_slack_user_id='U_BOB',
            ciphertext=wrap_envelope(MESSAGE_KINDS['user_list'],
                                     {'users': []}),
        )
        with seeqret_dir():
            _alice_sends(ws, alice, alice_sk, admin, [
                dict(app='myapp', env='prod', key='DB_PASS',
                     plaintext_value='s3cret'),
            ])

        result = runner.invoke(receive, ['--via', 'slack'])
        assert result.exit_code == 0, result.output
        assert 'Imported 1 secret(s)' in result.output

        with seeqret_dir():
            storage = SqliteStorage()
            rows = storage.fetch_secrets(app='myapp', env='prod',
                                         key='DB_PASS')
            assert len(rows) == 1
        # The envelope is still on slack for the onboarding pollers.
        assert len([m for m in ws.messages if m.get('files')]) == 1


def test_receive_updates_existing_secret(monkeypatch):
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        storage, admin, alice, alice_sk, ws = _receive_setup(runner)
        monkeypatch.setattr(
            cli_slack, 'SlackClient', lambda token: ws.client('U_BOB'))

        with seeqret_dir():
            storage = SqliteStorage()
            storage.add_secret(Secret(app='myapp', env='prod',
                                      key='DB_PASS',
                                      plaintext_value='old-value'))
            _alice_sends(ws, alice, alice_sk, admin, [
                dict(app='myapp', env='prod', key='DB_PASS',
                     plaintext_value='new-value'),
            ])

        result = runner.invoke(receive, ['--via', 'slack'])
        assert result.exit_code == 0, result.output

        with seeqret_dir():
            storage = SqliteStorage()
            rows = storage.fetch_secrets(app='myapp', env='prod',
                                         key='DB_PASS')
            assert rows[0].value == 'new-value'


def test_receive_rejects_unknown_sender(monkeypatch):
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        storage, admin, alice, alice_sk, ws = _receive_setup(runner)
        monkeypatch.setattr(
            cli_slack, 'SlackClient', lambda token: ws.client('U_BOB'))

        legacy = json.dumps({'version': 1, 'from': 'mallory',
                             'to': 'bob', 'secrets': [],
                             'signature': 'zzzzz'})
        send_blob(
            client=ws.client('U_MALLORY'),
            channel_id=CHANNEL,
            recipient_slack_user_id='U_BOB',
            ciphertext=legacy,
        )

        result = runner.invoke(receive, ['--via', 'slack'])
        assert result.exit_code != 0
        assert 'unknown Slack handle' in result.output
        # Blob NOT deleted -- fail closed.
        assert len([m for m in ws.messages if m.get('files')]) == 1
