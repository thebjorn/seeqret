import os
import seeqret
from seeqret.seeqret_add import add_key
from seeqret.seeqret_init import init_db, create_user_keys


# create a seeqret db and fill it with 500 secrets
def _create_db():
    create_user_keys('.', 'test', None)
    init_db('.', 'test', 'test@example.com')


def _fill_db():
    for i in range(200):
        add_key(f'key{i}', i)


def test_performance():
    # _create_db()
    # _fill_db()
    os.environ['SEEQRET'] = '.'
    import time
    start = time.time()
    for i in range(2750):
        seeqret.get('key42')
    print('Time taken:', time.time() - start)
    assert 0
