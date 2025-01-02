import os

import click

from .run_utils import cd
from .filterspec import FilterSpec
from .storage.sqlite_storage import SqliteStorage


@click.command()
@click.pass_context
@click.argument('filter')
def key(ctx, filter):
    """Remove a secret from the vault.
    """
    with cd(os.environ['SEEQRET']):
        storage = SqliteStorage()
        print("NAME:", FilterSpec(filter))
        storage.remove_secrets(**FilterSpec(filter).to_filterdict())
