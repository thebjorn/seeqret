import json
import sqlite3

import click

from seeqret import load_symetric_key, decrypt_string
from seeqret.db_utils import fetch_admin, fetch_user
from seeqret.filterspec import FilterSpec
from seeqret.seeqret_add import add_user, add_key
from seeqret.seeqrypt.nacl_backend import (
    public_key, load_private_key, asymetric_decrypt_string, hash_message,
    asymetric_encrypt_string,
)


def _validate_import_file(indata):
    """Validate json input.
    """
    errors = False

    # don't abort early, we want the user to receive _all_ the errors.
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
    """seeqret import-file <fname:json>
    """
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


def verify_hash(hash: str, message):
    msg = _extract_data(message)
    h = hash_message(msg.encode('utf-8'))
    if hash != h:
        msg = f'Invaolid hash ({hash}) expected: {h}'
        ctx = None
        try:
            ctx = click.get_current_context()
        except RuntimeError:
            pass
        if ctx is not None:
            ctx.fail(click.style(msg, fg='red'))
        else:
            raise RuntimeError(msg)
    return True


def _extract_data(message):
    """Extract all message values (so they can be hashed)
    """
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


def hash_secrets_message(message) -> str:
    """Hash all message values.
    """
    msg = _extract_data(message)
    return hash_message(msg.encode('utf-8'))


def export_secrets(to: str, fspec: FilterSpec):
    """seeqret export <user>

       Exports secrets from a SQLite database, preparing them for secure
       transfer to the specified receiver. The function retrieves secrets,
       decrypts them with a symmetric key, then encrypts the values with
       asymmetric encryption for the receiver. Finally, it generates a
       signature for the exported secrets for authenticity and integrity.

       Parameters:
           to (str): The recipient's username or the string 'self'
                     indicating the administrator. Secrets will be encrypted
                     using the public key of the specified user or
                     administrator.

       Returns:
           dict: A dictionary structured to contain metadata of the transaction
                 including the sender, receiver, and encrypted secrets ready
                 for transfer, along with a signature.

       Raises:
           Various exceptions may arise during database connection issues,
           encryption/decryption processes, or key-loading operations,
           depending on implementation details not shown here.
    """
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

    for (app, env, key, value) in fspec.filter(secrets):
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
