"""Tests for fetch_user() and unknown_user_error() handling.
"""
from click.testing import CliRunner

from seeqret.main import cli, init, introduction, load, export
from seeqret.run_utils import current_user
from seeqret.storage.sqlite_storage import SqliteStorage
from seeqret.seeqret_transfer import unknown_user_error
from tests.clirunner_utils import print_result

import click
import pytest


def _init_vault(runner):
    result = runner.invoke(init, [
        '.',
        '--user=' + current_user(),
        '--email=test@example.com',
    ])
    if result.exit_code != 0:  print_result(result)
    assert result.exit_code == 0


# -- fetch_user tests --

def test_fetch_user_returns_user():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        storage = SqliteStorage()
        user = storage.fetch_user(current_user())
        assert user is not None
        assert user.username == current_user()
        assert user.email == 'test@example.com'


def test_fetch_user_returns_none_for_unknown():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        storage = SqliteStorage()
        user = storage.fetch_user('nonexistent')
        assert user is None


# -- unknown_user_error tests --

def test_unknown_user_error_is_click_exception():
    err = unknown_user_error('baduser')
    assert isinstance(err, click.ClickException)


def test_unknown_user_error_contains_username():
    err = unknown_user_error('baduser')
    assert 'baduser' in err.format_message()


def test_unknown_user_error_contains_help_commands():
    err = unknown_user_error('baduser')
    msg = err.format_message()
    assert 'seeqret users' in msg
    assert 'seeqret add user' in msg
    assert 'seeqret introduction' in msg


# -- CLI integration: introduction with missing user --

def test_introduction_unknown_user(monkeypatch):
    """introduction command should handle missing user gracefully."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        monkeypatch.setattr('seeqret.main.current_user', lambda: 'nonexistent')
        result = runner.invoke(introduction)
        assert result.exit_code == 0
        assert 'not a user of this vault' in result.output


# -- CLI integration: load with unknown sender --

def test_load_unknown_sender():
    """load command should show friendly error for unknown sender."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        result = runner.invoke(load, [
            '-u', 'nonexistent',
            '-s', 'command',
            '-v', 'dummy_value',
        ])
        assert result.exit_code != 0
        assert 'nonexistent' in result.output


# -- CLI integration: export to unknown user --

def test_export_unknown_recipient():
    """export command should show friendly error for unknown recipient."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        result = runner.invoke(export, [
            '--to', 'nonexistent',
            '-f', '::::',
        ])
        assert result.exit_code != 0
        assert 'nonexistent' in result.output
