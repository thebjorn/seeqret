import json
import sqlite3

import click
import cryptography
import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from seeqret.seeqrypt.aes_fernet import encrypt_string, decrypt_string
from seeqret.seeqrypt.asym_nacl import asymetric_encrypt_string, sign_string, asymetric_decrypt_string
from seeqret.seeqrypt.utils import load_symetric_key
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key

from seeqret.utils import read_binary_file


def import_secrets(text):
    cipher = load_symetric_key('seeqret.key')
    private_key = load_pem_private_key(read_binary_file('private.key'), password=None)

    indata = json.loads(text)
    if 'from' not in indata:
        click.secho('Invalid file format, missing "from"', fg='red')
        return
    if 'data' not in indata:
        click.secho('Invalid file format, missing "data"', fg='red')
        return
    if 'signature' not in indata:
        click.secho('Invalid file format, missing "signature"', fg='red')
        return
    if 'to' not in indata:
        click.secho('Invalid file format, missing: "to"', fg='red')
        return

    signature = indata['signature']
    data = indata['data']
    from_user = indata['from']
    to_user = indata['to']

    user_pubkey = load_pem_public_key(from_user['pubkey'].encode('ascii'))
    sdata = []
    for secret in data:
        sdata.append(f"{secret['app']}:{secret['env']}[{secret['key']}] = {secret['val']}\n")
    sdata.sort()

    try:
        user_pubkey.verify(
            signature.encode('ascii'),
            ''.join(sdata).encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    except cryptography.exceptions.InvalidSignature:
        click.secho('Invalid signature', fg='red')
        # return

    # cn = sqlite3.connect('seeqrets.db')
    print("DATA:", data)
    for secret in data:
        val = asymetric_decrypt_string(private_key, secret['val'].encode('ascii'))

        print("INSERTING:", secret['app'], secret['env'], secret['key'], val)
        val = encrypt_string(cipher, val)
        # with cn:
        #     c = cn.cursor()
        #     c.execute('''
        #         INSERT INTO secrets (app, env, key, value) VALUES (?, ?, ?, ?);
        #     ''', (secret['app'], secret['env'], secret['key'], val))
        #     cn.commit()
    # cn.close()


def export_secrets(to):
    cipher = load_symetric_key('seeqret.key')

    cn = sqlite3.connect('seeqrets.db')
    user_pubkey = cn.execute('''
        select pubkey from users where username = ?
    ''', (to,)).fetchone()
    pubkey_string = user_pubkey[0]

    # convert string to public key object pkcs1
    pubkey = load_pem_public_key(pubkey_string.encode('ascii'))

    secrets = cn.execute('''
        select app, env, key, value
        from secrets
    ''').fetchall()
    admin = cn.execute('''
        select username, email, pubkey
        from users
        where id = 1
    ''').fetchone()

    res = dict(data=[], signature='')
    res['from'] = dict(username=admin[0], email=admin[1], pubkey=admin[2])
    res['to'] = dict(username=to)
    for (app, env, key, value) in secrets:
        val = decrypt_string(cipher, value).decode('utf-8')
        val = asymetric_encrypt_string(pubkey, val.encode('utf-8')).decode('ascii')
        res['data'].append(dict(app=app, env=env, key=key, val=val))
    cn.close()
    data = []
    for secret in res['data']:
        data.append(f"{secret['app']}:{secret['env']}[{secret['key']}] = {secret['val']}\n")
    data.sort()
    private_key = load_pem_private_key(read_binary_file('private.key'), password=None)
    res['signature'] = sign_string(private_key, ''.join(data).encode('utf-8')).decode('ascii')
    click.echo(json.dumps(res, indent=4))
    return res


def list_secrets():
    cipher = load_symetric_key('seeqret.key')
    cn = sqlite3.connect('seeqrets.db')
    secrets = cn.execute('''
        select app, env, key, value
        from secrets
    ''').fetchall()
    for (app, env, key, value) in secrets:
        val = decrypt_string(cipher, value).decode('utf-8')
        click.echo(f'Key: {app}:{env}[{key}] = {val}')
    cn.close()


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
    click.secho(f'Adding key: {key} with value: {value}', fg='blue')
    cipher = load_symetric_key('seeqret.key')
    cn = sqlite3.connect('seeqrets.db')
    try:
        with cn:
            c = cn.cursor()
            c.execute('''
                INSERT INTO secrets (app, env, key, value) VALUES (?, ?, ?, ?);
            ''', (app, env, key, encrypt_string(cipher, str(value).encode('utf-8'))))
            cn.commit()
    except sqlite3.IntegrityError:
        if click.confirm(f'Key already exists, overwrite?', default=True):
            with cn:
                c.execute('''
                    UPDATE secrets SET value = ?
                    WHERE app = ? AND env = ? AND key = ?;
                ''', (encrypt_string(cipher, str(value).encode('utf-8')),
                      app, env, key))

    secret = cn.execute('SELECT * FROM secrets WHERE key = ?', (key,)).fetchone()
    click.secho(f'Key: {app}:{env}[{key}] =', fg='green')
    click.secho(f'    {secret}', fg='green')
    cn.close()


def add_user(url, username, email):
    click.secho(f'Fetching public key: {url}', fg='blue')
    r = requests.get(url)
    if r.status_code != 200:
        click.secho(f'Failed to fetch public key: {url}', fg='red')
        return
    click.secho(f'Public key fetched:', fg='green')
    click.secho(r.text, fg='green')

    click.secho(f'Adding user: {username} with email: {email}', fg='blue')
    cn = sqlite3.connect('seeqrets.db')
    with cn:
        c = cn.cursor()
        c.execute('''
            INSERT INTO users (username, email, pubkey) VALUES (?, ?, ?);
        ''', (username, email, r.text))
        cn.commit()

    usr = cn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    click.secho(f'User added:', fg='green')
    click.secho(f'    {usr}', fg='green')
    cn.close()
