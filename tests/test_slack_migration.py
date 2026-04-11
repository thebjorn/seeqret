"""Tests for migration v003 (slack-exchange schema)."""

import os
import sqlite3

from click.testing import CliRunner

from seeqret.main import init
from seeqret.run_utils import current_user, seeqret_dir
from seeqret.storage.sqlite_storage import SqliteStorage
from seeqret.migrations.utils import (
    column_exists,
    current_version,
    table_exists,
)


def _init_vault(runner):
    result = runner.invoke(init, [
        '.',
        '--user=' + current_user(),
        '--email=test@example.com',
    ])
    assert result.exit_code == 0, result.output


def test_kv_table_created():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            cn = sqlite3.connect('seeqrets.db')
            try:
                assert table_exists(cn, 'kv')
            finally:
                cn.close()


def test_slack_columns_added_to_users():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            cn = sqlite3.connect('seeqrets.db')
            try:
                assert column_exists(cn, 'users', 'slack_handle')
                assert column_exists(cn, 'users', 'slack_key_fingerprint')
                assert column_exists(cn, 'users', 'slack_verified_at')
            finally:
                cn.close()


def test_migrations_version_is_3():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            cn = sqlite3.connect('seeqrets.db')
            try:
                assert current_version(cn) == 3
            finally:
                cn.close()


def test_kv_helpers_round_trip():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            storage.kv_set('foo', b'bar')
            assert storage.kv_get('foo') == b'bar'

            storage.kv_set('foo', b'baz')
            assert storage.kv_get('foo') == b'baz'

            storage.kv_delete('foo')
            assert storage.kv_get('foo') is None


def test_kv_delete_prefix_only_matches_prefix():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            storage.kv_set('slack.a', b'1')
            storage.kv_set('slack.b', b'2')
            storage.kv_set('other.c', b'3')

            storage.kv_delete_prefix('slack.')

            assert storage.kv_get('slack.a') is None
            assert storage.kv_get('slack.b') is None
            assert storage.kv_get('other.c') == b'3'
