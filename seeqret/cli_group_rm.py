# import os

import click

from .console_utils import as_table
from .run_utils import seeqret_dir
from .filterspec import FilterSpec
from .seeqret_transfer import resolve_user
from .storage.sqlite_storage import SqliteStorage
import logging

logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@click.argument('filter')
def key(ctx, filter):
    """Remove a secret from the vault specified by FILTER.
    """
    with seeqret_dir():
        storage = SqliteStorage()
        spec = FilterSpec(filter)
        logger.debug('remove_secrets: %s', filter)
        if not filter:
            click.secho("ERROR: can't remove all secrets", fg='red')
        secrets = storage.fetch_secrets(**spec.to_filterdict())
        as_table('app,env,key,value,type', secrets)
        if click.confirm('Delete secrets?'):
            print("DELETING SECRETS", [s.key for s in secrets])
        else:
            print("Aborting delete.")

        storage.remove_secrets(**spec.to_filterdict())

        click.secho("secrets deleted.", fg='green')


@click.command()
@click.pass_context
@click.argument('username')
@click.option('--yes', is_flag=True,
              help='Remove without prompting for confirmation.')
def user(ctx, username, yes):
    """Remove the user USERNAME from the vault.

       USERNAME may be a bare or qualified (user@host) name; a bare
       name is accepted when it matches exactly one user.

       The vault owner cannot be removed.
    """
    with seeqret_dir():
        storage = SqliteStorage()
        target = resolve_user(storage, username)
        logger.debug('remove_user: %s', target.username)

        admin = storage.fetch_admin()
        if admin and admin.username == target.username:
            ctx.fail(f"Cannot remove the vault owner: {target.username}.")

        as_table('username,email,publickey', [target])
        if not yes and not click.confirm(f'Remove user {target.username}?'):
            click.secho('Aborting.', fg='yellow')
            return

        storage.remove_user(target.username)
        click.secho(f"User {target.username} removed.", fg='green')
