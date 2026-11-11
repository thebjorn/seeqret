"""seeqret export users --to <user>  +  seeqret load
"""
import json
import os

from click.testing import CliRunner

from seeqret.main import init, export, load
from seeqret.models import User
from seeqret.storage.sqlite_storage import SqliteStorage
from tests.clirunner_utils import print_result


OTHER_PUBKEY = 'MBiGKmtpckXspJkmijIPXd8GrIAgAdLOoM4pZNOyDzw='
CAROL_PUBKEY = 'pW0RLdOR7kOy8EeG3lV0E8xa0XlP8rB8sCkMQq3m3Bw='


def _ok(result):
    if result.exit_code != 0:
        print_result(result)
    assert result.exit_code == 0
    return result


def _init(runner, dirname, user):
    """Create a vault for USER in DIRNAME; return (vault path, pubkey)."""
    os.mkdir(dirname)
    _ok(runner.invoke(init, [
        dirname, '--user=' + user, '--email=' + user + '.example.com',
    ]))
    vault = os.environ['SEEQRET']
    with open(os.path.join(vault, 'public.key')) as f:
        return vault, f.read().strip()


def _vaults(runner, monkeypatch):
    """alice's vault knows bob, carol and dave; bob's vault knows alice
       and a *different* dave.
    """
    alice_vault, alice_pub = _init(runner, 'a', 'alice@a')
    bob_vault, bob_pub = _init(runner, 'b', 'bob@b')

    monkeypatch.setenv('SEEQRET', alice_vault)
    storage = SqliteStorage(os.path.join(alice_vault, 'seeqrets.db'))
    storage.add_user(User('bob@b', 'bob@example.com', bob_pub))
    storage.add_user(User('carol@c', 'carol@example.com', CAROL_PUBKEY,
                          name='Carol Ø'))
    storage.add_user(User('dave@d', 'dave@example.com', OTHER_PUBKEY))

    storage = SqliteStorage(os.path.join(bob_vault, 'seeqrets.db'))
    storage.add_user(User('alice@a', 'alice@example.com', alice_pub))
    storage.add_user(User('dave@d', 'dave@example.com', CAROL_PUBKEY))
    return alice_vault, bob_vault


def test_export_users_round_trip(monkeypatch):
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        alice_vault, bob_vault = _vaults(runner, monkeypatch)

        monkeypatch.setenv('SEEQRET', alice_vault)
        _ok(runner.invoke(export, ['users', '--to', 'bob', '-o', 'u.json']))
        with open('u.json', encoding='utf-8') as f:
            text = f.read()
        data = json.loads(text)
        assert data['kind'] == 'users'
        assert data['to']['username'] == 'bob@b'
        # the user list is encrypted
        assert 'carol@c' not in text

        monkeypatch.setenv('SEEQRET', bob_vault)
        result = _ok(runner.invoke(load, ['-u', 'alice', '-f', 'u.json']))
        assert 'Added user: carol@c' in result.output
        assert 'dave@d already exists with a different public key' \
            in result.output
        assert '1 added, 2 skipped.' in result.output

        storage = SqliteStorage(os.path.join(bob_vault, 'seeqrets.db'))
        carol = storage.fetch_user('carol@c')
        assert carol.pubkey == CAROL_PUBKEY
        assert carol.name == 'Carol Ø'
        # existing users are left untouched
        assert storage.fetch_user('dave@d').pubkey == CAROL_PUBKEY
        assert [u.username for u in storage.fetch_users()] == [
            'alice@a', 'bob@b', 'carol@c', 'dave@d',
        ]

        # loading again adds nothing
        result = _ok(runner.invoke(load, ['-u', 'alice', '-f', 'u.json']))
        assert '0 added, 3 skipped.' in result.output


def test_load_users_from_wrong_sender_fails(monkeypatch):
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        alice_vault, bob_vault = _vaults(runner, monkeypatch)

        monkeypatch.setenv('SEEQRET', alice_vault)
        _ok(runner.invoke(export, ['users', '--to', 'bob', '-o', 'u.json']))

        monkeypatch.setenv('SEEQRET', bob_vault)
        result = runner.invoke(load, ['-u', 'dave', '-f', 'u.json'])
        assert result.exit_code == 1
        assert 'Could not decrypt the users export' in result.output
        storage = SqliteStorage(os.path.join(bob_vault, 'seeqrets.db'))
        assert storage.fetch_user('carol@c') is None


def test_export_without_to_still_fails(monkeypatch):
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _vaults(runner, monkeypatch)
        result = runner.invoke(export, [])
        assert result.exit_code == 2
        assert "Missing option '--to'" in result.output


def test_export_users_out_requires_single_recipient(monkeypatch):
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        alice_vault, _ = _vaults(runner, monkeypatch)
        monkeypatch.setenv('SEEQRET', alice_vault)
        result = runner.invoke(
            export, ['users', '--to', 'all', '-o', 'u.json'])
        assert result.exit_code == 2
        assert 'single recipient' in result.output


def test_load_secrets_from_file(monkeypatch):
    """`seeqret load -f` reads the file (it used to json-parse the path)."""
    from seeqret.models import Secret
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        alice_vault, bob_vault = _vaults(runner, monkeypatch)

        monkeypatch.setenv('SEEQRET', alice_vault)
        storage = SqliteStorage(os.path.join(alice_vault, 'seeqrets.db'))
        storage.add_secret(Secret(app='app', env='prod', key='K',
                                  plaintext_value='v'))
        result = _ok(runner.invoke(export, ['--to', 'bob', '-f', '::']))
        text = result.output.split('Seeqrets for bob@b:', 1)[1]
        with open('s.json', 'w', encoding='utf-8') as f:
            f.write(text)

        monkeypatch.setenv('SEEQRET', bob_vault)
        _ok(runner.invoke(load, ['-u', 'alice', '-f', 's.json']))
        storage = SqliteStorage(os.path.join(bob_vault, 'seeqrets.db'))
        [secret] = storage.fetch_secrets(app='app', env='prod', key='K')
        assert secret.value == 'v'


def _run_load_line(runner, line):
    """Run a pasted `seeqret load ...` LINE through the load command."""
    import shlex
    args = shlex.split(line)
    assert args[:2] == ['seeqret', 'load']
    return runner.invoke(load, args[2:])


def test_export_users_command_round_trip(monkeypatch):
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        alice_vault, bob_vault = _vaults(runner, monkeypatch)

        monkeypatch.setenv('SEEQRET', alice_vault)
        result = _ok(runner.invoke(
            export, ['users', '--to', 'bob', '-s', 'command']))
        lines = result.output.strip().splitlines()
        # one line per user except the recipient: alice, carol, dave
        assert len(lines) == 3
        assert all(line.startswith('seeqret load -ualice@a -scommand '
                                   '-vusers:1:') for line in lines)
        assert 'carol@c' not in result.output

        monkeypatch.setenv('SEEQRET', bob_vault)
        outputs = [_ok(_run_load_line(runner, line)).output
                   for line in lines]
        assert sum('Added user: carol@c' in o for o in outputs) == 1
        assert sum('different public key' in o for o in outputs) == 1

        storage = SqliteStorage(os.path.join(bob_vault, 'seeqrets.db'))
        assert storage.fetch_user('carol@c').name == 'Carol Ø'
        assert storage.fetch_user('dave@d').pubkey == CAROL_PUBKEY

        # a line loaded with the wrong sender is rejected
        result = _run_load_line(
            runner, lines[0].replace('-ualice@a', '-udave@d'))
        assert result.exit_code == 1
        assert 'Could not decrypt the users export' in result.output


def test_export_users_rejects_other_serializers(monkeypatch):
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        alice_vault, _ = _vaults(runner, monkeypatch)
        monkeypatch.setenv('SEEQRET', alice_vault)
        result = runner.invoke(export, ['users', '--to', 'bob', '-s', 'env'])
        assert result.exit_code == 2
        assert "'env' is not one of" in result.output
