import os
import re
import sqlite3
from contextlib import contextmanager

from ..run_utils import get_seeqret_dir

from ..models import User, Secret
from .storage import Storage
from logging import getLogger

logger = getLogger(__name__)


def one_line(txt):
    res = txt.replace('\n', ' ').strip()
    return re.sub(r'\s+', ' ', res).strip()


def glob_to_sql(glob_pattern: str) -> str:
    """
    Convert a glob-like pattern (with * and ?) to a SQL WHERE clause string
    and parameters.

    Args:
        glob_pattern (str): Glob pattern to convert.

    Returns:
        tuple: A tuple with a SQL WHERE clause and parameter list.
    """
    sql_pattern = glob_pattern.replace("*", "%").replace("?", "_")
    return sql_pattern


class SqliteStorage(Storage):
    def __init__(self, fname='seeqrets.db'):
        super().__init__('sqlite')
        self.fname = fname

    @contextmanager
    def connection(self):
        path = os.path.join(get_seeqret_dir(), self.fname)
        logger.debug('Connecting to SQLite: %s', path)
        # print('Connecting to SQLite: %s' % path)
        cn = sqlite3.connect(path)
        with cn:
            yield cn
        cn.close()
        logger.debug('Closed connection to SQLite: %s', path)

    def execute_sql(self, sql, **filters):
        with self.connection() as cn:
            order_by = ""
            if isinstance(sql, tuple):
                sql, order_by = sql
            params = []
            where = []
            if filters:
                sql += " where "
                for k, v in filters.items():
                    op = 'like' if re.search(r'[\[.*]', v) else '='
                    where.append(f"{k} {op} ? ")
                    params.append(glob_to_sql(v) if op == 'like' else v)
            sql += " and ".join(where) + order_by
            logger.debug('Executing SQL: %s params: %s',
                         one_line(sql), params)
            res = cn.execute(sql, params).fetchall()
            logger.info('Retrieved: %d records', len(res))
            logger.debug('Result: %s', res)
            return res

    def add_user(self, user: User):
        with self.connection() as cn:
            c = cn.cursor()
            c.execute('''
                insert into users (username, email, pubkey)
                values (?, ?, ?);
            ''', (
                user.username,
                user.email,
                user.pubkey
            ))
            cn.commit()

        return self.fetch_users(username=user.username)

    def fetch_users(self, **filters):
        logger.debug('fetch_users: %s', filters)
        sql = ("""
            select username, email, pubkey
            from users
        """, " order by username ")
        return [User(*rec)
                for rec in self.execute_sql(sql, **filters)]

    def update_secret(self, secret: Secret):
        with self.connection() as cn:
            cn.execute('''
                UPDATE secrets SET value = ?
                WHERE app = ? AND env = ? AND key = ?;
            ''', (
                secret._value,
                secret.app, secret.env, secret.key
            ))
            cn.commit()

    def add_secret(self, secret: Secret):
        with self.connection() as cn:
            sql = """
                insert into secrets (app, env, key, value, type)
                values (?, ?, ?, ?, ?);
            """
            cn.execute(sql, (
                secret.app,
                secret.env,
                secret.key,
                secret._value,
                secret.type
            ))
            cn.commit()

    def fetch_secrets(self, **filters):
        logger.debug('fetch_secrets: %s', filters)
        sql = """
            select app, env, key, value, type
            from secrets
        """
        return [Secret(*rec)
                for rec in self.execute_sql(sql, **filters)]

    def remove_secrets(self, **filters):
        sql = """
            delete from secrets
        """
        self.execute_sql(sql, **filters)

    def fetch_admin(self):
        logger.debug('fetch_admin: %s', self)
        with self.connection() as cn:
            admin_rec = cn.execute("""
                select username, email, pubkey
                from users
                where id = 1
            """).fetchone()
        if admin_rec is None:
            return None
        return User(*admin_rec)
