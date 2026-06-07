"""Tests for resolve_recipients() (`seeqret export --to all`).
"""
from click.testing import CliRunner

from seeqret.main import init
from seeqret.models import User
from seeqret.run_utils import current_user
from seeqret.storage.sqlite_storage import SqliteStorage
from seeqret.seeqret_transfer import resolve_recipients
from tests.clirunner_utils import print_result


PUBKEY = 'MBiGKmtpckXspJkmijIPXd8GrIAgAdLOoM4pZNOyDzw='


def _init_vault(runner):
    result = runner.invoke(init, [
        '.',
        '--user=' + current_user(),
        '--email=test@example.com',
    ])
    if result.exit_code != 0:
        print_result(result)
    assert result.exit_code == 0


def test_all_expands_to_other_users_excluding_owner():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        storage = SqliteStorage()
        storage.add_user(User('alice@mac', 'a@example.com', PUBKEY))
        storage.add_user(User('bob@hpc', 'b@example.com', PUBKEY))

        recipients = resolve_recipients(storage, ['all'])
        assert recipients == ['alice@mac', 'bob@hpc']
        assert current_user() not in recipients


def test_all_with_only_owner_is_empty():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        storage = SqliteStorage()
        assert resolve_recipients(storage, ['all']) == []


def test_all_deduplicates_named_user():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        storage = SqliteStorage()
        storage.add_user(User('alice@mac', 'a@example.com', PUBKEY))
        storage.add_user(User('bob@hpc', 'b@example.com', PUBKEY))

        recipients = resolve_recipients(storage, ['bob@hpc', 'all'])
        assert recipients == ['bob@hpc', 'alice@mac']


def test_self_is_passed_through():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        storage = SqliteStorage()
        storage.add_user(User('alice@mac', 'a@example.com', PUBKEY))

        recipients = resolve_recipients(storage, ['self', 'all'])
        assert recipients == ['self', 'alice@mac']


def test_named_user_resolved():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        storage = SqliteStorage()
        storage.add_user(User('alice@mac', 'a@example.com', PUBKEY))

        # bare name resolves to the unique qualified user
        assert resolve_recipients(storage, ['alice']) == ['alice@mac']
