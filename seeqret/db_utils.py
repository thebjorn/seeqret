from os import abort

import click


def fetch_admin(cn):
    admin = cn.execute('''
        select username, email, pubkey
        from users
        where id = 1
    ''').fetchone()
    if not admin:
        click.secho('No admin user', fg='red')
        abort()
    return dict(username=admin[0], email=admin[1], pubkey=admin[2])


def fetch_user(cn, username):
    user = cn.execute('''
        select username, email, pubkey
        from users
        where username = ?
    ''', [username]).fetchone()
    if not user:
        return None
    return dict(username=user[0], email=user[1], pubkey=user[2])
