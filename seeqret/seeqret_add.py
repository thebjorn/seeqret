import os
import sqlite3
from os import abort

import click
import requests

from seeqret.console_utils import as_table
from seeqret.storage.sqlite_storage import SqliteStorage

from seeqret.filterspec import FilterSpec
from seeqret.seeqrypt.aes_fernet import encrypt_string
from seeqret.seeqrypt.utils import load_symetric_key


def fetch_pubkey_from_url(url):

    r = requests.get(url)
    if r.status_code != 200:
        ctx = None
        try:
            ctx = click.get_current_context()
        except AttributeError:
            # during testing we don't neccessarily have a context...
            raise RuntimeError(f'Could not fetch pubkey from url: {url}')
        ctx.fail(click.style(f'Failed to fetch public key: {url}', fg='red'))
    click.secho('Public key fetched.', fg='green')
    return r.text


# seeqret list
def list_secrets(fspec: FilterSpec):
    storage = SqliteStorage()
    as_table("App,Env,Key,Value,Type",
             storage.fetch_secrets(**fspec.to_filterdict()))


# seeqret users
def list_users():
    storage = SqliteStorage()
    as_table('username,email,publickey',
             storage.fetch_users())


# seeqret key ...
def add_key(key, value, app='*', env='*'):
    if ':' in key or ':' in app or ':' in env:
        click.secho('Colon `:` is not valid in key, app, or env', fg='red')
        abort()

    print("ADD:KEY:cwd", os.getcwd())
    print("DB:EXISTS:", os.path.exists('seeqrets.db'))
    print(os.listdir('.'))
    # click.secho(f'Adding key: {key} with value: {value}', fg='blue')
    click.secho(f'Adding key: {key}..', fg='blue')
    cipher = load_symetric_key('seeqret.key')
    cn = sqlite3.connect('seeqrets.db')
    try:
        with cn:
            c = cn.cursor()
            c.execute('''
                INSERT INTO secrets (app, env, key, value) VALUES (?, ?, ?, ?);
            ''', (
                app,
                env,
                key,
                encrypt_string(cipher, str(value).encode('utf-8'))
            ))
            cn.commit()
    except sqlite3.IntegrityError:
        if click.confirm('Key already exists, overwrite?', default=True):
            with cn:
                c.execute('''
                    UPDATE secrets SET value = ?
                    WHERE app = ? AND env = ? AND key = ?;
                ''', (encrypt_string(cipher, str(value).encode('utf-8')),
                      app, env, key))

    secret = cn.execute('''
        SELECT * FROM secrets WHERE key = ?
    ''', (key,)).fetchone()
    if secret:
        click.secho(
            f'..successfully added: {app}:{env}[{key}]', fg='green'
        )
    else:
        click.secho(
            f'Error: {app}:{env}[{key}] not written to database', fg='red'
        )
    cn.close()


# seeqret add user ...
def add_user(pubkey, username, email):
    click.secho(f'Adding user: {username} with email: {email}', fg='blue')
    cn = sqlite3.connect('seeqrets.db')
    with cn:
        c = cn.cursor()
        c.execute('''
            INSERT INTO users (username, email, pubkey) VALUES (?, ?, ?);
        ''', (username, email, pubkey))
        cn.commit()

    usr = cn.execute('''
        SELECT * FROM users WHERE username = ?
    ''', (username,)).fetchone()
    click.secho('User added:', fg='green')
    click.secho(f'    {usr}', fg='green')
    cn.close()
