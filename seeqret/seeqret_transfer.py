import os
import sys
from textwrap import dedent

import click

from .filterspec import FilterSpec
from .seeqrypt.nacl_backend import (
    load_private_key,
)
from .storage.sqlite_storage import SqliteStorage


def unknown_user_error(username: str) -> click.ClickException:
    """Build a ClickException with helpful guidance for an unknown user.
    """
    cmd = lambda s: click.style(s, fg='green')
    return click.ClickException(
        click.style(f"Unknown user: '{username}'.", fg='bright_red') + "\n" + dedent(
        f"""
        Use 
          - {cmd('seeqret users')} to list known users.
          - {cmd('seeqret add user')} to add a new user.
          - {cmd('seeqret edit user')} to edit an existing user.
          - {cmd('seeqret rm user')} to remove an existing user.

        The other user needs to send you their public key. They must run:

            > seeqret introduction
            Please add me to your vault!
            {click.style('seeqret add user --username usr --email usr@example.com --pubkey ThkU/1234567890...', fg='blue')}

        and send the command to you (can be pasted into an insecure channel like 
        email). When you run the command, your vault will know about the new user
        (and their public key).
        """
    ))


def import_secrets(sender, file, value, serializer):
    storage = SqliteStorage()
    receiver = storage.fetch_admin()
    sender_user = storage.fetch_user(sender)
    if not sender_user:
        raise unknown_user_error(sender)
    sender = sender_user

    s = serializer(
        sender=sender,
        receiver=receiver,
        receiver_private_key=load_private_key('private.key'),
    )
    secrets = s.load(file or value)
    for secret in secrets:
        storage.add_secret(secret)


def export_secrets(ctx, *, to: str, fspec: FilterSpec, serializer,
                   out=None, windows=False, linux=False):
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
        receiver = storage.fetch_user(to)
        if not receiver:
            raise unknown_user_error(to)

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

    if out:
        click.echo(f"Writing secrets to: {out} ({os.path.join(ctx.obj['curdir'], out)})")
        with open(os.path.join(ctx.obj['curdir'], out), 'w') as f:
            f.write(res)
    else:
        click.echo(res)
    return res
