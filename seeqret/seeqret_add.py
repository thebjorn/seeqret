import json
import sqlite3
from os import abort
from rich.console import Console
from rich.table import Table

import click
import requests

from seeqret.seeqrypt.aes_fernet import encrypt_string, decrypt_string
from seeqret.seeqrypt.nacl_backend import (
    public_key,
    asymetric_encrypt_string,
    asymetric_decrypt_string, load_private_key, hash_message,
)
from seeqret.seeqrypt.utils import load_symetric_key


def _validate_import_file(indata):
    errors = False
    if 'from' not in indata:
        click.secho('Invalid file format, missing "from"', fg='red')
        errors = True
    if 'username' not in indata['from']:
        click.secho('Invalid file format, missing "from.username"', fg='red')
        errors = True
    if 'email' not in indata['from']:
        click.secho('Invalid file format, missing "from.email"', fg='red')
        errors = True
    if 'pubkey' not in indata['from']:
        click.secho('Invalid file format, missing "from.pubkey"', fg='red')
        errors = True
    if 'data' not in indata:
        click.secho('Invalid file format, missing "data"', fg='red')
        errors = True
    if 'signature' not in indata:
        click.secho('Invalid file format, missing "signature"', fg='red')
        errors = True
    if 'to' not in indata:
        click.secho('Invalid file format, missing: "to"', fg='red')
        errors = True
    if 'username' not in indata['to']:
        click.secho('Invalid file format, missing "to.username"', fg='red')
        errors = True

    return not errors


def import_secrets(indata):
    if not _validate_import_file(indata):
        click.secho('Invalid file format.', fg='red')
        return
    click.secho("file format ok...", fg='green')

    signature = indata['signature']
    data = indata['data']
    from_user = indata['from']
    to_user = indata['to']['username']

    cn = sqlite3.connect('seeqrets.db')
    admin = fetch_admin(cn)
    if to_user != admin['username']:
        click.secho(
            f'Incorrect to.username {to_user}, not {admin["username"]}',
            fg='red'
        )
        return
    click.secho("Correct `to` field.")

    # cipher = load_symetric_key('seeqret.key')
    sender_pubkey = public_key(from_user['pubkey'])
    receiver_private_key = load_private_key('private.key')
    for item in data:
        item['val'] = asymetric_decrypt_string(item['val'],
                                               receiver_private_key,
                                               sender_pubkey)

    click.secho("verifying signature...")
    verify_hash(signature, indata)
    click.secho('Successfully validated file', fg='green')

    if not fetch_user(cn, from_user['username']):
        add_user(
            from_user['pubkey'],
            from_user['username'],
            from_user['email']
        )
    else:
        click.secho('Found sender', fg='green')
    cn.close()

    # click.echo(json.dumps(indata, indent=4))

    for secret in data:
        add_key(
            secret['key'],
            secret['val'],
            secret['app'],
            secret['env'],
            # secret['type']
        )


def verify_hash(hash, message):
    msg = _extract_data(message)
    if hash != hash_message(msg.encode('utf-8')):
        click.secho('Invalid hash', fg='red')
        abort()
    return True


def _extract_data(message):
    # extract all message values
    data = []
    for secret in message['data']:
        data.append(f"{secret['app']}:{secret['env']}:{secret['key']}:{secret['val']}\n")  # noqa
    data.sort()
    sender = message['from']
    data.append(
        f'From:{sender["username"]}|{sender["email"]}|{sender["pubkey"]}\n'
    )
    data.append(f'To:{message["to"]["username"]}\n')
    msg = ''.join(data)
    return msg


def hash_secrets_message(message):
    msg = _extract_data(message)
    return hash_message(msg.encode('utf-8'))


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


def export_secrets(to):
    cipher = load_symetric_key('seeqret.key')
    sender_pkey = load_private_key('private.key')

    cn = sqlite3.connect('seeqrets.db')
    if to == 'self':
        admin = fetch_admin(cn)
        pubkey_string = admin['pubkey']
    else:
        user_pubkey = cn.execute('''
            select pubkey from users where username = ?
        ''', (to,)).fetchone()
        pubkey_string = user_pubkey[0]

    # convert string to public key object pkcs1
    receiver_pubkey = public_key(pubkey_string)

    secrets = cn.execute('''
        select app, env, key, value
        from secrets
    ''').fetchall()
    admin = fetch_admin(cn)

    res = dict(data=[])
    res['from'] = admin
    res['to'] = dict(username=to if to != 'self' else admin['username'])

    for (app, env, key, value) in secrets:
        val = decrypt_string(cipher, value).decode('utf-8')
        res['data'].append(dict(app=app, env=env, key=key, val=val))
    cn.close()

    res["signature"] = hash_secrets_message(res)

    for item in res["data"]:
        item["val"] = asymetric_encrypt_string(
            item['val'], sender_pkey, receiver_pubkey
        )

    click.echo(json.dumps(res, indent=4))
    return res


def list_secrets():
    res = []
    cipher = load_symetric_key('seeqret.key')
    cn = sqlite3.connect('seeqrets.db')
    secrets = cn.execute('''
        select app, env, key, value
        from secrets
    ''').fetchall()

    table = Table()
    table.add_column("App")
    table.add_column("Env")
    table.add_column("Key")
    table.add_column("Value")
    for (app, env, key, value) in secrets:
        val = decrypt_string(cipher, value).decode('utf-8')
        table.add_row(app, env, key, val)

    console = Console()
    console.print(table)
    cn.close()
    return res


def list_users():
    cn = sqlite3.connect('seeqrets.db')
    users = cn.execute('''
        select id, username, email
        from users
    ''').fetchall()
    for (id, username, email) in users:
        if id == 1:
            click.secho(f'User: {username} = {email} (admin)', fg='blue')
        else:
            click.echo(f'User: {username} = {email}')
    cn.close()


def add_key(key, value, app='*', env='*'):
    if ':' in key or ':' in app or ':' in env:
        click.secho('Colon `:` is not valid in key, app, or env', fg='red')
        abort()

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


def fetch_pubkey_from_url(url):
    r = requests.get(url)
    if r.status_code != 200:
        click.secho(f'Failed to fetch public key: {url}', fg='red')
        abort()
    click.secho('Public key fetched.', fg='green')
    return r.text


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
        SELECT * FROM users WHERE username = ?'
    ''', (username,)).fetchone()
    click.secho('User added:', fg='green')
    click.secho(f'    {usr}', fg='green')
    cn.close()
