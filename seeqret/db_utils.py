import os
import sqlite3

from seeqret.run_utils import get_seeqret_dir
# from os import abort

# import click


# def fetch_admin(cn):
#     admin = cn.execute('''
#         select username, email, pubkey
#         from users
#         where id = 1
#     ''').fetchone()
#     if not admin:
#         click.secho('No admin user', fg='red')
#         abort()
#     return dict(username=admin[0], email=admin[1], pubkey=admin[2])


# def fetch_user(cn, username):
#     user = cn.execute('''
#         select username, email, pubkey
#         from users
#         where username = ?
#     ''', [username]).fetchone()
#     if not user:
#         return None
#     return dict(username=user[0], email=user[1], pubkey=user[2])


def debug_fetch_users():
    cn = sqlite3.connect(os.path.join(get_seeqret_dir(), 'seeqrets.db'))
    with cn:
        return [rec[0] for rec in cn.execute("""
            select username
            from users
            order by username
        """)]


def debug_secrets():
    cn = sqlite3.connect(os.path.join(get_seeqret_dir(), 'seeqrets.db'))
    with cn:
        return [rec for rec in cn.execute("""
            select app, env, key, value
            from secrets
            order by app, env, key
        """)]
