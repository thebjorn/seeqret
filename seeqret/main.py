import os
from pathlib import Path

import click

# from .context import Context
from . import seeqret_init, seeqret_add
from .utils import is_writable, cd, read_json

DIRNAME = Path(__file__).parent

# os.environ['SEEQRET'] = os.getcwd() + r'\seeqret'


@click.group()
# @click.pass_context
def cli():
    pass


@cli.command()
def upgrade():
    """Upgrade the database to the latest version
    """
    with cd(os.environ['SEEQRET']):
        seeqret_init.upgrade_db()


@cli.command()
def list():
    """List the contents of the vault
    """
    with cd(os.environ['SEEQRET']):
        return seeqret_add.list_secrets()


@cli.command()
def users():
    """List the users in the vault
    """
    # print("SEEQRET:DIR:", os.environ['SEEQRET'])
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
    text = read_json(fname)
    with cd(os.environ['SEEQRET']):
        seeqret_add.import_secrets(text)


@cli.command()
@click.argument(
    'dir',
    default='.',
    # prompt='Directory to initialize seeqret in',
)
@click.option(
    '--user',
    prompt=True,
    default=lambda: f"{os.environ['USERDOMAIN']}\\{os.environ['USERNAME']}"
)
@click.option('--email', prompt=True)
@click.option('--pubkey', default=None)
@click.option('--key', default=None)
def init(dir, user, email, pubkey=None, key=None):
    """Initialize a new vault
    """
    dirname = Path(dir).resolve()
    vault_dir = dirname / 'seeqret'

    # we want to create dirname / seeqret

    if not dirname.exists():
        click.echo(f'The parent of the vault: {dirname} must exist.')
        return

    if not is_writable(dirname):
        click.echo(f'The parent of the vault: {dirname} must be writable.')
        return

    if vault_dir.exists():
        if not is_writable(vault_dir):
            click.echo(
                f'The vault: {vault_dir} exists and is not writeable, '
                'you must delete it manually.'
            )
            return
        click.confirm(
            f'The vault: {vault_dir} already exists, overwrite contents?',
            default=True, abort=True)
        # remove_directory(vault_dir)

    seeqret_init.secrets_init(dirname, user, email, pubkey, key)


@cli.group()
def add():
    """Add a new secret, key or user
    """
    pass


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
        click.secho(f'Fetching public key: {url}', fg='blue')
        pubkey = seeqret_add.fetch_pubkey_from_url(url)
        seeqret_add.add_user(pubkey, username, email)


@add.command()
@click.argument('name')
@click.argument('value')
@click.option('--app', default='*')
@click.option('--env', default='*')
def key(name: str, value: str, app: str = None, env: str = None):
    """Add a new key/value pair.
    """
    click.echo(
        f'Adding a new key: {name}, value: {value}, app: {app}, env: {env}'
    )

    with cd(os.environ['SEEQRET']):
        seeqret_add.add_key(name, value, app, env)
