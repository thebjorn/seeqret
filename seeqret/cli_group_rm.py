# import os

import click

from .console_utils import as_table
from .run_utils import seeqret_dir
from .filterspec import FilterSpec
from .storage.sqlite_storage import SqliteStorage
import logging

logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@click.argument('filter')
def key(ctx, filter):
    """Remove a secret from the vault.
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
