import os
import textwrap
from pathlib import Path

import click

from .context import Context
from . import seeqret_init, seeqret_add
from .utils import remove_directory, is_writable, cd, read_file

DIRNAME = Path(__file__).parent

os.environ['SEEQRET'] = os.getcwd() + r'\seeqret'


@click.group()
# @click.pass_context
def cli():
    pass


@cli.command()
def list():
    """List the contents of the vault
    """
    with cd(os.environ['SEEQRET']):
        seeqret_add.list_secrets()


@cli.command()
def users():
    """List the users in the vault
    """
    with cd(os.environ['SEEQRET']):
        seeqret_add.list_users()


@cli.command()
@click.argument('to')
def export(to):
    """Export the vault to a user
    """
    with cd(os.environ['SEEQRET']):
        seeqret_add.export_secrets(to)


@cli.command()
@click.argument('fname')
def import_file(fname):
    """Import a vault from a file
    """
    text = read_file(fname)
    with cd(os.environ['SEEQRET']):
        seeqret_add.import_secrets(text)


@cli.command()
@click.argument(
    'dir',
    default='.',
    # prompt='Directory to initialize seeqret in',
)
@click.option('--user', prompt=True, default=lambda: f"{os.environ['USERDOMAIN']}\\{os.environ['USERNAME']}")
@click.option('--email', prompt=True)
def init(dir, user, email):
    """Initialize a new vault
    """
    ctx = Context()
    dirname = Path(dir).resolve()
    vault_dir = dirname / 'seeqret'
    ctx.vault_dir = vault_dir
    ctx.user = user
    ctx.email = email

    # we want to create dirname / seeqret

    if not dirname.exists():
        click.echo(f'The parent of the vault: {dirname} must exist.')
        return

    if not is_writable(dirname):
        click.echo(f'The parent of the vault: {dirname} must be writable.')
        return

    if vault_dir.exists():
        if not is_writable(vault_dir):
            click.echo(f'The vault: {vault_dir} exists and is not writeable, you must delete it manually.')
            return
        click.confirm(f'The vault: {vault_dir} already exists, overwrite contents?', default=True, abort=True)
        # remove_directory(vault_dir)

    # if click.confirm(f'Initialize new seeqret vault in {dirname/"seeqret"}?', default=True, abort=True):
    seeqret_init.secrets_init(dirname, user, email, ctx)


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
@click.option('--url', prompt=True)
@click.option('--username', prompt=True)
@click.option('--email', prompt=True)
def user(url, username, email):
    """Add a new user to the vault from a public key.

       If the public key is on github, the url is the raw url, e.g.

       https://raw.githubusercontent.com/username/project/refs/heads/main/public.key
    """
    click.echo(f'Adding a new user, from {url}')
    with cd(os.environ['SEEQRET']):
        seeqret_add.add_user(url, username, email)


@add.command()
@click.argument('name')
@click.argument('value')
@click.option('--app', default='*')
@click.option('--env', default='*')
def key(name: str, value: str, app:str=None, env:str=None):
    """Add a new key/value pair.
    """
    click.echo(f'Adding a new key name: {name}, value: {value}, app: {app}, env: {env}')

    with cd(os.environ['SEEQRET']):
        seeqret_add.add_key(name, value, app, env)

# @click.command()
# def generate():
#     click.echo('Generating a new key pair')
#
#
# @cli.command()
# def encrypt():
#     click.echo('Encrypting a message')
#
#
# @cli.command()
# def decrypt():
#     click.echo('Decrypting a message')
