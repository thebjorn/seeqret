"""Tests for seeqret.slack.config (Fernet-wrapped kv)."""

from click.testing import CliRunner

from seeqret.main import init
from seeqret.run_utils import current_user, seeqret_dir
from seeqret.slack.config import (
    SLACK_KEYS,
    slack_config_clear_all,
    slack_config_delete,
    slack_config_get,
    slack_config_set,
    slack_config_snapshot,
)
from seeqret.storage.sqlite_storage import SqliteStorage


def _init_vault(runner):
    result = runner.invoke(init, [
        '.',
        '--user=' + current_user(),
        '--email=test@example.com',
    ])
    assert result.exit_code == 0, result.output


def test_round_trip_string_value():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            slack_config_set(storage, SLACK_KEYS['user_token'], 'xoxp-fake')
            assert slack_config_get(
                storage, SLACK_KEYS['user_token']
            ) == 'xoxp-fake'


def test_round_trip_object_value():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            val = {'a': 1, 'b': [2, 3], 'c': 'x'}
            slack_config_set(storage, 'slack.custom', val)
            assert slack_config_get(storage, 'slack.custom') == val


def test_missing_key_returns_none():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            assert slack_config_get(storage, 'slack.never_set') is None


def test_set_overwrites():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            slack_config_set(storage, SLACK_KEYS['team_name'], 'v1')
            slack_config_set(storage, SLACK_KEYS['team_name'], 'v2')
            assert slack_config_get(
                storage, SLACK_KEYS['team_name']
            ) == 'v2'


def test_delete_removes_value():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            slack_config_set(
                storage, SLACK_KEYS['user_token'], 'xoxp-x',
            )
            slack_config_delete(storage, SLACK_KEYS['user_token'])
            assert slack_config_get(
                storage, SLACK_KEYS['user_token']
            ) is None


def test_clear_all_wipes_slack_prefix_only():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            slack_config_set(
                storage, SLACK_KEYS['user_token'], 'tok',
            )
            slack_config_set(
                storage, SLACK_KEYS['team_id'], 'T1',
            )
            storage.kv_set('other.key', b'unrelated')

            slack_config_clear_all(storage)

            assert slack_config_get(
                storage, SLACK_KEYS['user_token']
            ) is None
            assert slack_config_get(
                storage, SLACK_KEYS['team_id']
            ) is None
            assert storage.kv_get('other.key') == b'unrelated'


def test_snapshot_returns_every_key():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            slack_config_set(
                storage, SLACK_KEYS['team_name'], 'ntseeqrets',
            )
            snap = slack_config_snapshot(storage)
            assert snap['team_name'] == 'ntseeqrets'
            assert snap['user_token'] is None
            assert snap['channel_id'] is None


def test_stored_blob_is_actually_encrypted():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            slack_config_set(
                storage, SLACK_KEYS['user_token'], 'xoxp-SECRET',
            )
            blob = storage.kv_get(SLACK_KEYS['user_token'])
            assert blob is not None
            # The raw bytes must NOT contain the plaintext token.
            assert b'xoxp-SECRET' not in blob
