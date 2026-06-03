"""Tests for resolve_user() and ambiguous_user_error() (issue #25).
"""
from click.testing import CliRunner

from seeqret.main import init
from seeqret.models import User
from seeqret.run_utils import current_user
from seeqret.storage.sqlite_storage import SqliteStorage
from seeqret.seeqret_transfer import (
    ambiguous_user_error, resolve_user, unknown_user_error,
)
from tests.clirunner_utils import print_result

import click
import pytest


PUBKEY = 'MBiGKmtpckXspJkmijIPXd8GrIAgAdLOoM4pZNOyDzw='


def _init_vault(runner):
    result = runner.invoke(init, [
        '.',
        '--user=' + current_user(),
        '--email=test@example.com',
    ])
    if result.exit_code != 0:  print_result(result)
    assert result.exit_code == 0


def test_resolve_exact_qualified():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        storage = SqliteStorage()
        storage.add_user(User('bjorn@host1', 'b@example.com', PUBKEY))
        user = resolve_user(storage, 'bjorn@host1')
        assert user.username == 'bjorn@host1'


def test_resolve_bare_name_falls_back_to_unique_qualified():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        storage = SqliteStorage()
        storage.add_user(User('bjorn@host1', 'b@example.com', PUBKEY))
        user = resolve_user(storage, 'bjorn')
        assert user.username == 'bjorn@host1'


def test_resolve_exact_bare_beats_prefix_match():
    """A legacy bare user must win over a qualified user with the same name."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        storage = SqliteStorage()
        storage.add_user(User('bjorn', 'legacy@example.com', PUBKEY))
        storage.add_user(User('bjorn@host1', 'b@example.com', PUBKEY))
        user = resolve_user(storage, 'bjorn')
        assert user.username == 'bjorn'
        assert user.email == 'legacy@example.com'


def test_resolve_bare_name_ambiguous():
    """The issue #25 scenario: same username on two machines."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        storage = SqliteStorage()
        storage.add_user(User('bjorn@oldpc', 'b@example.com', PUBKEY))
        storage.add_user(User('bjorn@newpc', 'b@example.com', PUBKEY))
        with pytest.raises(click.ClickException) as exc_info:
            resolve_user(storage, 'bjorn')
        msg = exc_info.value.format_message()
        assert 'Ambiguous' in msg
        assert 'bjorn@oldpc' in msg
        assert 'bjorn@newpc' in msg


def test_resolve_unknown_user():
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        storage = SqliteStorage()
        with pytest.raises(click.ClickException) as exc_info:
            resolve_user(storage, 'nonexistent')
        assert 'nonexistent' in exc_info.value.format_message()


def test_resolve_qualified_name_does_not_fall_back():
    """A qualified name that doesn't exist must not match other users."""
    runner = CliRunner(env=dict(TESTING="TRUE"))
    with runner.isolated_filesystem():
        _init_vault(runner)
        storage = SqliteStorage()
        storage.add_user(User('bjorn@host1', 'b@example.com', PUBKEY))
        with pytest.raises(click.ClickException):
            resolve_user(storage, 'bjorn@host2')


def test_ambiguous_user_error_is_click_exception():
    users = [
        User('bjorn@oldpc', 'b@example.com', PUBKEY),
        User('bjorn@newpc', 'b@example.com', PUBKEY),
    ]
    err = ambiguous_user_error('bjorn', users)
    assert isinstance(err, click.ClickException)
    msg = err.format_message()
    assert 'bjorn@oldpc' in msg
    assert 'bjorn@newpc' in msg
    assert 'seeqret users' in msg
