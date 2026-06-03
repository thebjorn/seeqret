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
    cmd = lambda s: click.style(s, fg='green')  # noqa: E731
    cmd_blue = lambda s: click.style(s, fg='blue')  # noqa: E731
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
                {cmd_blue('seeqret add user --username usr --email usr@.. --pubkey ThkU/1234...')}

            and send the command to you (can be pasted into an insecure channel like
            email). When you run the command, your vault will know about the new user
            (and their public key).
            """
        )
    )


def ambiguous_user_error(username: str,
                         candidates: list) -> click.ClickException:
    """Build a ClickException for a bare username matching several users.
    """
    cmd = lambda s: click.style(s, fg='green')  # noqa: E731
    names = '\n            '.join(
        f'- {cmd(u.username)} <{u.email}>' for u in candidates
    )
    return click.ClickException(
        click.style(f"Ambiguous user: '{username}'.", fg='bright_red')
        + "\n" + dedent(
            f"""
            The name matches more than one user:

            {names}

            Use the full user@host form to disambiguate
            ({cmd('seeqret users')} to list known users).
            """
        )
    )


def resolve_user(storage, name: str):
    """Resolve NAME to a user in the vault.

       Tries an exact username match first.  A bare name (no @host
       qualifier) falls back to matching a single qualified user, so
       existing vaults and habits keep working.  Raises a ClickException
       if the name is unknown or ambiguous.
    """
    users = storage.fetch_users()
    for user in users:
        if user.username == name:
            return user
    if '@' not in name:
        matches = [u for u in users if u.username.startswith(name + '@')]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ambiguous_user_error(name, matches)
    raise unknown_user_error(name)


def import_secrets(sender, file, value, serializer):
    storage = SqliteStorage()
    receiver = storage.fetch_admin()
    sender = resolve_user(storage, sender)

    s = serializer(
        sender=sender,
        receiver=receiver,
        receiver_private_key=load_private_key('private.key'),
    )
    secrets = s.load(file or value)
    for secret in secrets:
        storage.upsert_secret(secret)


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
        receiver = resolve_user(storage, to)

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
