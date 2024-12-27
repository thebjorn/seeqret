import sqlite3

from seeqret.fileutils import remove_file_if_exists
from seeqret.migrations.utils import *


def test_table_exists():
    cn = sqlite3.connect('test_table_exists.db')
    with cn:
        assert not table_exists(cn, 'test')
        cn.executescript("""
            create table if not exists test (
              id integer primary key
            )
        """)
        assert table_exists(cn, 'test')
    cn.close()
    remove_file_if_exists('test_table_exists.db')


def test_index_exists():
    cn = sqlite3.connect('test_index_exists.db')
    with cn:
        assert not index_exists(cn, 'test', 'idx_test_foo')
        cn.executescript("""
            create table if not exists test (
                id integer primary key,
                foo text not null
            )
        """)
        cn.commit()
        cn.executescript("""
            create unique index if not exists idx_test_foo
            on test (foo)
        """)
        cn.commit()
        assert index_exists(cn, 'test', 'idx_test_foo')
    cn.close()
    remove_file_if_exists('test_index_exists.db')
