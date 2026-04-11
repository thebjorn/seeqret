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

    def _where_field(self, field: str, value: str) -> tuple[str, list]:
        op = 'like' if re.search(r'[\[.*]', value) else '='
        return f"{field} {op} ? ", [glob_to_sql(value) if op == 'like' else value]

    def _where_field_or(self, field: str, values: list) -> tuple[str, list]:
        where = []
        params = []
        for v in values:
            if v == '*':
                where_clause = f"{field} = ?"
                params.append(v)
            else:
                where_clause, where_params = self._where_field(field, v)
                params.extend(where_params)
            where.append(where_clause)
        return '(' + ' or '.join(where) + ')', params

    def _where_clause(self, filters: dict) -> tuple[str, list]:
        where = []
        params = []
        if filters:
            for k, v in filters.items():
                if ',' in v:
                    where_clause, where_params = self._where_field_or(k, v.split(','))
                else:
                    where_clause, where_params = self._where_field(k, v)
                where.append(where_clause)
                params.extend(where_params)
            return ' where ' + ' and '.join(where), params
        return '', []

    def execute_sql(self, sql, **filters):
        with self.connection() as cn:
            order_by = ""
            if isinstance(sql, tuple):
                sql, order_by = sql
            where, params = self._where_clause(filters)
            sql += where + order_by
            logger.debug('Executing SQL: %s params: %s',
                         one_line(sql), params)
            res = cn.execute(sql, params).fetchall()
            logger.info('Retrieved: %d records', len(res))
            logger.debug('Result: %s', res)
            return res

    # ---- User helpers ------------------------------------------------

    _USER_COLS_V3 = (
        "username, email, pubkey, "
        "slack_handle, slack_key_fingerprint, slack_verified_at"
    )
    _USER_COLS_V2 = "username, email, pubkey"

    @staticmethod
    def _user_from_row(rec):
        """Hydrate a User from a row of either column layout.

           Rows may or may not include the ``slack_*`` columns; they
           are only present on migration v3 and later.
        """
        if len(rec) == 3:
            return User(*rec)
        return User(
            rec[0], rec[1], rec[2],
            slack_handle=rec[3],
            slack_key_fingerprint=rec[4],
            slack_verified_at=rec[5],
        )

    def _has_slack_columns(self, cn) -> bool:
        """Cached check for the presence of migration v3 columns.

           Used so the storage layer stays backward-compatible on
           vaults that have not yet run ``seeqret upgrade`` --
           otherwise every CLI command would crash on an unavoidable
           ``validate_current_user()`` call before the operator ever
           gets a chance to upgrade.
        """
        if getattr(self, '_slack_cols_present', None) is None:
            row = cn.execute(
                "select count(*) from pragma_table_info('users')"
                " where name='slack_handle'"
            ).fetchone()
            self._slack_cols_present = bool(row and row[0])
        return self._slack_cols_present

    def _user_cols(self, cn) -> str:
        """Return the SELECT column list appropriate for the schema.
        """
        return self._USER_COLS_V3 if self._has_slack_columns(cn) \
            else self._USER_COLS_V2

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

    def fetch_user(self, username: str):
        """Fetch a single user by username.

           Returns a ``User`` instance or ``None`` if no user with
           that username exists.
        """
        logger.debug('fetch_user: %s', username)
        with self.connection() as cn:
            cols = self._user_cols(cn)
            rec = cn.execute(f"""
                select {cols}
                from users
                where username = ?
            """, (username,)).fetchone()
        if rec is None:
            return None
        return self._user_from_row(rec)

    def fetch_users(self, **filters):
        logger.debug('fetch_users: %s', filters)
        with self.connection() as cn:
            cols = self._user_cols(cn)
        sql = (f"""
            select {cols}
            from users
        """, " order by username ")
        return [self._user_from_row(rec)
                for rec in self.execute_sql(sql, **filters)]

    def update_user_slack(self, username: str,
                          slack_handle=None,
                          slack_key_fingerprint=None,
                          slack_verified_at=None):
        """Persist the Slack identity binding on a user row.

           All three ``slack_*`` fields are written together so the
           binding stays internally consistent: a stored handle
           always matches its verified fingerprint and timestamp.
        """
        with self.connection() as cn:
            cn.execute("""
                update users
                set slack_handle = ?,
                    slack_key_fingerprint = ?,
                    slack_verified_at = ?
                where username = ?
            """, (
                slack_handle,
                slack_key_fingerprint,
                slack_verified_at,
                username,
            ))
            cn.commit()

    # ---- Encrypted key-value store ----------------------------------

    def kv_get(self, key: str) -> bytes | None:
        """Fetch a raw encrypted blob from the kv table.

           Callers are responsible for Fernet-unwrapping the
           returned value. Returns ``None`` when no row exists.
        """
        with self.connection() as cn:
            rec = cn.execute(
                "select encrypted_value from kv where key = ?",
                (key,),
            ).fetchone()
        if rec is None:
            return None
        return bytes(rec[0]) if rec[0] is not None else None

    def kv_set(self, key: str, encrypted_value: bytes) -> None:
        """Upsert a kv row.

           The value must already be Fernet-encrypted; this method
           does not touch the vault's symmetric key.
        """
        import time
        now = int(time.time())
        with self.connection() as cn:
            cn.execute("""
                insert into kv (key, encrypted_value, updated_at)
                values (?, ?, ?)
                on conflict(key) do update set
                    encrypted_value = excluded.encrypted_value,
                    updated_at = excluded.updated_at
            """, (key, encrypted_value, now))
            cn.commit()

    def kv_delete(self, key: str) -> None:
        """Delete a single kv row by key.
        """
        with self.connection() as cn:
            cn.execute("delete from kv where key = ?", (key,))
            cn.commit()

    def kv_delete_prefix(self, prefix: str) -> None:
        """Delete every kv row whose key starts with *prefix*.

           Used by ``seeqret slack logout`` to wipe all ``slack.*``
           entries in a single call.
        """
        with self.connection() as cn:
            cn.execute("delete from kv where key like ?", (prefix + '%',))
            cn.commit()

    def kv_list_prefix(self, prefix: str):
        """List ``(key, updated_at)`` pairs with a given prefix.
        """
        with self.connection() as cn:
            return cn.execute(
                "select key, updated_at from kv"
                " where key like ? order by key",
                (prefix + '%',),
            ).fetchall()

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
            cols = self._user_cols(cn)
            admin_rec = cn.execute(f"""
                select {cols}
                from users
                where id = 1
            """).fetchone()
        if admin_rec is None:
            return None
        return self._user_from_row(admin_rec)
