"""Tests for seeqret.slack.identity (fingerprint-verified bindings)."""

import pytest
from click.testing import CliRunner
from nacl.public import PrivateKey
from nacl import encoding

from seeqret.main import init
from seeqret.models import User
from seeqret.run_utils import current_user, seeqret_dir
from seeqret.slack.identity import (
    bind_slack_handle,
    compute_fingerprint,
    find_user_by_slack_handle,
    require_verified_binding,
)
from seeqret.storage.sqlite_storage import SqliteStorage


def _init_vault(runner):
    result = runner.invoke(init, [
        '.',
        '--user=' + current_user(),
        '--email=test@example.com',
    ])
    assert result.exit_code == 0, result.output


def _make_pubkey() -> str:
    """Generate a fresh NaCl public key encoded as base64 string."""
    pk = PrivateKey.generate()
    return encoding.Base64Encoder.encode(bytes(pk.public_key)).decode('ascii')


def test_compute_fingerprint_is_5_hex_chars():
    u = User('bob', 'b@b.com', _make_pubkey())
    fp = compute_fingerprint(u)
    assert len(fp) == 5
    assert all(c in '0123456789abcdef' for c in fp)
    # Stable on repeated calls
    assert compute_fingerprint(u) == fp


def test_bind_persists_handle_fingerprint_timestamp():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            storage.add_user(User('bob', 'bob@test.com', _make_pubkey()))

            _, fp = bind_slack_handle(storage, 'bob', 'bob_slk')

            refetched = storage.fetch_user('bob')
            assert refetched.slack_handle == 'bob_slk'
            assert refetched.slack_key_fingerprint == fp
            assert refetched.slack_verified_at is not None
            assert refetched.slack_verified_at > 0


def test_require_verified_binding_passes_for_fresh_binding():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            storage.add_user(User('bob', 'bob@test.com', _make_pubkey()))
            bind_slack_handle(storage, 'bob', 'bob_slk')

            _, handle = require_verified_binding(storage, 'bob')
            assert handle == 'bob_slk'


def test_require_verified_binding_refuses_unlinked_user():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            storage.add_user(User('bob', 'bob@test.com', _make_pubkey()))

            with pytest.raises(ValueError, match='not linked'):
                require_verified_binding(storage, 'bob')


def test_require_verified_binding_refuses_on_fingerprint_drift():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            storage.add_user(User('bob', 'bob@test.com', _make_pubkey()))
            bind_slack_handle(storage, 'bob', 'bob_slk')

            # Rotate bob's key directly in the DB, simulating tampering.
            import sqlite3
            cn = sqlite3.connect('seeqrets.db')
            try:
                cn.execute(
                    'update users set pubkey = ? where username = ?',
                    (_make_pubkey(), 'bob'),
                )
                cn.commit()
            finally:
                cn.close()

            with pytest.raises(ValueError, match='no longer matches'):
                require_verified_binding(storage, 'bob')


def test_find_user_by_slack_handle_returns_match():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            storage.add_user(User('carol', 'c@t.com', _make_pubkey()))
            bind_slack_handle(storage, 'carol', 'carol_slk')

            u = find_user_by_slack_handle(storage, 'carol_slk')
            assert u is not None
            assert u.username == 'carol'


def test_find_user_by_slack_handle_returns_none_for_unknown():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            assert find_user_by_slack_handle(storage, 'nobody') is None
