import os
from pathlib import Path

import click

from .context import Context
from . import seeqret_init


@click.group()
# @click.pass_context
def cli():
    pass


@cli.command()
@click.argument(
    'dir',
    default='.',
    # prompt='Directory to initialize seeqret in',
)
@click.option('--user', prompt=True, default=lambda: f"{os.environ['USERDOMAIN']}\\{os.environ['USERNAME']}")
def init(dir, user):
    ctx = Context()
    dir = Path(dir).resolve()
    ctx.vault_dir = dir

    if click.confirm(f'Initialize new seeqret vault in {dir}?'):
        seeqret_init.secrets_init(dir)


@cli.group()
def add():
    """Add a new secret, key or user
    """
    pass


@add.command()
def secret():
    click.echo('Adding a new secret')
    # seeqret_add.add_secret()



@add.command()
def key():
    click.echo('Adding a new key')
    # seeqret_add.add_key()


@add.command()
def user():
    click.echo('Adding a new user')
    # seeqret_add.add_user()


@click.command()
def generate():
    click.echo('Generating a new key pair')


@cli.command()
def encrypt():
    click.echo('Encrypting a message')


@cli.command()
def decrypt():
    click.echo('Decrypting a message')
