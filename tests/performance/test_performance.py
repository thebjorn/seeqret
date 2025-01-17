import pytest
import os
import seeqret
from seeqret.run_utils import seeqret_dir
from seeqret.models import Secret
from seeqret.seeqret_init import init_db, create_user_keys
from seeqret.fileutils import remove_file_if_exists
from seeqret.storage.sqlite_storage import SqliteStorage


# create a seeqret db and fill it with 500 secrets
def _create_db():
    create_user_keys('.', 'test', None)
    init_db('.', 'test', 'test@example.com')


def _secret_i(i):
    return Secret(
        app='*',
        env='*',
        key=f'key{i}',
        plaintext_value=str(i),
        type='str'
    )

def _fill_db():
    with seeqret_dir():
        storage = SqliteStorage()
        for i in range(200):
            storage.add_secret(_secret_i(i))


# @pytest.mark.skip(reason="don't test performance in CI")
def test_performance():
    os.environ['TESTING'] = "TRUE"
    _create_db()
    os.environ['SEEQRET'] = '.'
    _fill_db()
    import time
    start = time.time()
    for i in range(2750):
        seeqret.get('key42')
    duration = time.time() - start
    print('Time taken:', duration)
    assert duration < 3
    remove_file_if_exists('private.key')
    remove_file_if_exists('public.key')
    remove_file_if_exists('seeqret.key')
    remove_file_if_exists('seeqrets.db')
