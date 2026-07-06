"""Tests for the jseeqret-parity core modules: vault registry,
   envelope, json-crypt load, two-phase merge, user-list serializer,
   and onboarding storage.
"""
import json

import pytest
from click.testing import CliRunner

from seeqret import merge, vault_registry
from seeqret.cli_group_add import key
from seeqret.main import init
from seeqret.models import Secret, User
from seeqret.onboarding import expire_stale_onboarding
from seeqret.run_utils import cd
from seeqret.seeqrypt.nacl_backend import generate_private_key
from seeqret.serializers.envelope import parse_envelope, wrap_envelope
from seeqret.serializers.jsoncrypt_serializer import JsonCryptSerializer
from seeqret.serializers.user_list_serializer import UserListSerializer
from seeqret.storage.sqlite_storage import SqliteStorage


# ---- vault registry ---------------------------------------------------

def test_vault_registry(tmp_path, monkeypatch):
    reg_file = tmp_path / '.seeqret' / 'vaults.json'
    monkeypatch.setattr(vault_registry, 'registry_path',
                        lambda: str(reg_file))

    assert vault_registry.registry_list() == []
    vault_registry.registry_add('work', str(tmp_path / 'work'))
    vault_registry.registry_add('home', str(tmp_path / 'home'))
    vault_registry.registry_use('work')

    entries = vault_registry.registry_list()
    assert [e['name'] for e in entries] == ['home', 'work']
    assert vault_registry.registry_default() == 'work'
    assert vault_registry.registry_resolve('home') == \
        str(tmp_path / 'home')

    # the on-disk shape must match jseeqret exactly
    data = json.loads(reg_file.read_text())
    assert data['_default'] == 'work'
    assert set(data) == {'_default', 'work', 'home'}

    with pytest.raises(ValueError):
        vault_registry.registry_add('_default', str(tmp_path))
    with pytest.raises(ValueError):
        vault_registry.registry_use('nope')

    # removing the default clears the marker
    assert vault_registry.registry_remove('work')
    assert vault_registry.registry_default() is None
    assert not vault_registry.registry_remove('work')


# ---- envelope ----------------------------------------------------------

def test_envelope_roundtrip():
    text = wrap_envelope('invite', dict(email='a@b.c'))
    env = parse_envelope(text)
    assert env['kind'] == 'invite'
    assert env['payload'] == dict(email='a@b.c')
    assert env['version'] == 1


def test_envelope_legacy_payload():
    legacy = json.dumps(dict(version=1, secrets=[]))
    env = parse_envelope(legacy)
    assert env['kind'] == 'secret'
    assert env['version'] is None
    assert env['payload'] == dict(version=1, secrets=[])

    env = parse_envelope('not json at all')
    assert env['kind'] == 'secret'


def test_envelope_unknown_kind_rejected():
    with pytest.raises(ValueError):
        wrap_envelope('gossip', {})


# ---- json-crypt --------------------------------------------------------

def _init_vault(runner, user='test@host1', email='test@example.com'):
    result = runner.invoke(init, ['.', f'--user={user}',
                                  f'--email={email}'])
    assert result.exit_code == 0, result.output


def test_jsoncrypt_payload_shape_and_load():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        runner.invoke(key, ['FOO', 'BAR', '--app=myapp', '--env=dev'])

        with cd('seeqret'):
            storage = SqliteStorage()
            admin = storage.fetch_admin()
            from seeqret.seeqret_transfer import vault_private_key
            s = JsonCryptSerializer(
                sender=admin, receiver=admin,
                sender_private_key=vault_private_key(),
            )
            payload = s.dumps(storage.fetch_secrets(), 'linux')

            data = json.loads(payload)
            # jseeqret shape: usernames, not user objects
            assert data['from'] == 'test@host1'
            assert data['to'] == 'test@host1'
            assert len(data['signature']) == 5
            rec = data['secrets'][0]
            assert set(rec) == {'app', 'env', 'key', 'value', 'type',
                                'updated_at'}
            assert rec['value'] != 'BAR'   # encrypted

            loader = JsonCryptSerializer(
                sender=admin, receiver=admin,
                receiver_private_key=vault_private_key(),
            )
            secrets = loader.load(payload)
            assert len(secrets) == 1
            assert secrets[0].key == 'FOO'
            assert secrets[0].value == 'BAR'

            assert JsonCryptSerializer.sender_username(payload) == \
                'test@host1'


# ---- two-phase merge ---------------------------------------------------

def test_merge_two_phase():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        runner.invoke(key, ['FOO', 'local', '--app=a', '--env=e'])
        runner.invoke(key, ['SAME', 'x', '--app=a', '--env=e'])

        with cd('seeqret'):
            storage = SqliteStorage()
            incoming = [
                Secret(app='a', env='e', key='FOO',
                       plaintext_value='theirs', updated_at=999),
                Secret(app='a', env='e', key='SAME',
                       plaintext_value='x'),
                Secret(app='a', env='e', key='NEW',
                       plaintext_value='n'),
            ]
            plan = merge.plan_secret_merge(storage, incoming)
            assert len(plan['additions']) == 1
            assert len(plan['identical']) == 1
            assert len(plan['conflicts']) == 1

            summary = merge.conflict_summary(plan)
            assert summary[0]['id'] == 'a:e:FOO'
            assert summary[0]['local_value'] == 'local'
            assert summary[0]['incoming_value'] == 'theirs'

            # unresolved conflicts must abort before any write
            with pytest.raises(ValueError):
                merge.apply_secret_merge(storage, plan)
            assert storage.fetch_secrets(key='NEW') == []

            result = merge.apply_secret_merge(
                storage, plan, {'a:e:FOO': 'theirs'})
            assert result == dict(added=1, updated=1, kept=0,
                                  skipped=1, count=2)
            assert storage.fetch_secrets(key='FOO')[0].value == 'theirs'
            assert storage.fetch_secrets(key='NEW')[0].value == 'n'


def test_merge_newer_strategy():
    # raw `value` bytes avoid the eager Fernet encryption that
    # plaintext_value triggers (no vault needed for this test)
    conflict = dict(
        local=Secret(app='a', env='e', key='K',
                     value=b'old', updated_at=100),
        incoming=Secret(app='a', env='e', key='K',
                        value=b'new', updated_at=200),
    )
    assert merge.resolve_conflict(conflict, 'newer') == 'theirs'
    conflict['incoming'].updated_at = 50
    assert merge.resolve_conflict(conflict, 'newer') == 'mine'
    # ties keep local (conservative)
    conflict['incoming'].updated_at = 100
    assert merge.resolve_conflict(conflict, 'newer') == 'mine'


# ---- user-list serializer ----------------------------------------------

def test_user_list_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv('SEEQRET', str(tmp_path))
    sender_key = generate_private_key(str(tmp_path / 'private.key'))
    receiver_key = generate_private_key()

    import base64
    sender = User('tl@host', 'tl@x.com',
                  base64.b64encode(
                      bytes(sender_key.public_key)).decode('ascii'))
    receiver = User('nu@host', 'nu@x.com',
                    base64.b64encode(
                        bytes(receiver_key.public_key)).decode('ascii'))
    team = [User('a@h', 'a@x.com', sender.pubkey, name='Alice')]

    payload = UserListSerializer(
        sender=sender, receiver=receiver,
        sender_private_key=sender_key,
    ).dumps(team)

    data = json.loads(payload)
    assert data['from'] == 'tl@host'
    assert 'Alice' not in data['users']    # encrypted

    records = UserListSerializer(
        sender=sender,
        receiver_private_key=receiver_key,
    ).load(payload)
    assert records == [dict(username='a@h', email='a@x.com',
                            pubkey=sender.pubkey, name='Alice')]


# ---- onboarding storage -------------------------------------------------

def test_onboarding_rows():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with cd('seeqret'):
            storage = SqliteStorage()
            storage.onboarding_create(dict(
                email='new@x.com', name='New', slack_user_id='U1',
                project_filter='myapp:*:*', state='invited'))
            row = storage.onboarding_get('new@x.com')
            assert row['state'] == 'invited'
            assert row['name'] == 'New'

            storage.onboarding_update('new@x.com', dict(
                username='new@host', fingerprint='abcde',
                state='introduced'))
            row = storage.onboarding_get('new@x.com')
            assert row['username'] == 'new@host'
            assert row['state'] == 'introduced'

            # unknown fields are ignored, not written
            storage.onboarding_update('new@x.com', dict(email='hax'))
            assert storage.onboarding_get('new@x.com') is not None

            assert len(storage.onboarding_list()) == 1

            # TTL expiry flips open rows only
            expired = expire_stale_onboarding(
                storage, now=row['created_at'] + 8 * 86400)
            assert expired == 1
            assert storage.onboarding_get('new@x.com')['state'] == \
                'expired'

            storage.onboarding_delete('new@x.com')
            assert storage.onboarding_get('new@x.com') is None


# ---- facade two-phase import --------------------------------------------

def test_facade_import_conflict_flow():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        runner.invoke(key, ['FOO', 'original', '--app=m', '--env=p'])
        runner.invoke(key, ['BAR', 'bar', '--app=m', '--env=p'])

        from seeqret.gui.vault_facade import VaultFacade
        facade = VaultFacade()

        export = facade.export_secrets(to=['self'])
        payload = export['results'][0]['output']

        # diverge the local copy, then re-import the export
        facade.update_secret_value(app='m', env='p', key='FOO',
                                   value='changed')
        preview = facade.import_preview(content=payload)
        assert preview['needs_resolution']
        assert preview['identical'] == 1          # BAR
        assert len(preview['conflicts']) == 1     # FOO
        assert preview['conflicts'][0]['id'] == 'm:p:FOO'

        result = facade.import_apply({'m:p:FOO': 'theirs'})
        assert result['updated'] == 1
        assert facade.list_secrets('m:p:FOO')[0]['value'] == 'original'
