# import sqlite3
import sys

import click

# from .db_utils import fetch_admin, fetch_user
from .filterspec import FilterSpec
# from .seeqret_add import add_user, add_key
from .seeqrypt.nacl_backend import (
    # public_key,
    load_private_key,
    # asymetric_decrypt_string,
    # hash_message,
)
from .storage.sqlite_storage import SqliteStorage


def import_secrets(sender, file, value, serializer):
    storage = SqliteStorage()
    receiver = storage.fetch_admin()
    sender = storage.fetch_users(username=sender)[0]

    s = serializer(
        sender=sender,
        receiver=receiver,
        receiver_private_key=load_private_key('private.key'),
    )
    secrets = s.load(file or value)
    for secret in secrets:
        storage.add_secret_obj(secret)


def export_secrets(to: str, fspec: FilterSpec, serializer, windows, linux):
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
    storage = SqliteStorage()

    admin = storage.fetch_admin()
    if to == 'self':
        receiver = admin
    else:
        receiver = storage.fetch_users(username=to)[0]

    s = serializer(
        sender=admin,
        receiver=receiver,
        sender_private_key=load_private_key('private.key'),
    )

    secrets = storage.fetch_secrets(**fspec.to_filterdict())
    system = sys.platform  # default to current system
    if windows:
        system = 'win32'
    if linux:
        system = 'linux'
    res = s.dumps(secrets, system)

    # print("SECRETS:---------------------")
    click.echo(res)
    # print("/SECRETS:---------------------")
    return res
