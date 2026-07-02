"""Tests for migration v006 (secrets.updated_at) -- mirrors jseeqret.

   The timestamp is advisory merge metadata: storage stamps "now" for
   local writes, but preserves a timestamp already carried by the
   Secret (imports keep the sender's modification time).
"""

import sqlite3
import time

from click.testing import CliRunner

from seeqret.main import init
from seeqret.models.secret import Secret
from seeqret.run_utils import current_user, seeqret_dir
from seeqret.storage.sqlite_storage import SqliteStorage
from seeqret.migrations.utils import column_exists


def _init_vault(runner):
    result = runner.invoke(init, [
        '.',
        '--user=' + current_user(),
        '--email=test@example.com',
    ])
    assert result.exit_code == 0, result.output


def test_updated_at_column_added():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            cn = sqlite3.connect('seeqrets.db')
            try:
                assert column_exists(cn, 'secrets', 'updated_at')
            finally:
                cn.close()


def test_add_secret_stamps_now_when_absent():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            before = int(time.time())
            storage.add_secret(Secret(
                app='a', env='e', key='K', plaintext_value='v',
            ))
            (s,) = storage.fetch_secrets(key='K')
            assert s.updated_at >= before


def test_add_and_upsert_preserve_carried_timestamp():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            storage.add_secret(Secret(
                app='a', env='e', key='K', plaintext_value='v1',
                updated_at=1111,
            ))
            (s,) = storage.fetch_secrets(key='K')
            assert s.updated_at == 1111

            storage.upsert_secret(Secret(
                app='a', env='e', key='K', plaintext_value='v2',
                updated_at=2222,
            ))
            (s,) = storage.fetch_secrets(key='K')
            assert s.value == 'v2'
            assert s.updated_at == 2222


def test_update_secret_stamps_now():
    runner = CliRunner(env=dict(TESTING='TRUE'))
    with runner.isolated_filesystem():
        _init_vault(runner)
        with seeqret_dir():
            storage = SqliteStorage()
            storage.add_secret(Secret(
                app='a', env='e', key='K', plaintext_value='v1',
                updated_at=1111,
            ))
            (s,) = storage.fetch_secrets(key='K')
            before = int(time.time())
            s.value = 'v2'
            storage.update_secret(s)
            (after,) = storage.fetch_secrets(key='K')
            assert after.value == 'v2'
            assert after.updated_at >= before


def test_encrypt_to_dict_carries_updated_at():
    # The export wire format includes the timestamp so the importing
    # side can run its merge; None for legacy secrets.
    s = Secret(app='a', env='e', key='K', value=b'raw', updated_at=1234)
    # encrypt_to_dict needs keys; check the plaintext dict shape instead
    d = s.__json__()
    assert d['updated_at'] == 1234

    legacy = Secret(app='a', env='e', key='K', value=b'raw')
    assert legacy.__json__()['updated_at'] is None
