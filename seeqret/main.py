import json
import os
from pathlib import Path

import click
from click import Context

import seeqret.seeqret_transfer
# from .context import Context
from . import seeqret_init, seeqret_add, cd
from .console_utils import as_table, dochelp
from .fileutils import is_writable
from .filterspec import FilterSpec
from .serializers.serializer import SERIALIZERS
import logging


DIRNAME = Path(__file__).parent


@click.group()
@click.pass_context
@click.option('-L', '--log', default="ERROR")
def cli(ctx, log):
    logging.basicConfig(level=getattr(logging, log))


@cli.command()
def info():
    "debugging"
    with Context(cli) as ctx:
        info = ctx.to_info_dict()
        print(json.dumps(info, indent=4))


@cli.command()
def upgrade():
    """Upgrade the database to the latest version
    """
    with cd(os.environ['SEEQRET']):
        seeqret_init.upgrade_db()


@cli.command()
@click.option('-f', '--filter', default='*', show_default=True,
              help='filterspec (see XXX)')
def list(filter):
    """List the contents of the vault
    """
    with cd(os.environ['SEEQRET']):
        return seeqret_add.list_secrets(FilterSpec(filter))


@cli.command()
def users():
    """List the users in the vault
    """
    # print("SEEQRET:DIR:", os.environ['SEEQRET'])
    with cd(os.environ['SEEQRET']):
        seeqret_add.list_users()


@cli.command()
def serializers():
    """List available serializers.
    """
    as_table('Name, tag, version, description',
             [(
                 cls.__name__,
                 cls.tag,
                 str(cls.version),
                 dochelp(cls)
             ) for cls in SERIALIZERS.values()])


@cli.command()
@click.pass_context
@click.argument('to')
@click.option('-f', '--filter', default='',
              help='A seeqret filter string (see XXX) ')
@click.option(
    '-s', '--serializer', default='json-crypt',
    help='Name of serializer to use (`seeqret serializers` to list).')
@click.option('-w', '--windows', default=False, is_flag=True,
              help='Export to windows format.')
@click.option('-l', '--linux', default=False, is_flag=True,
              help='Export to linux format.')
def export(ctx, to, filter, serializer='json-crypt',
           windows=False, linux=False):
    """Export the vault to a user
    """
    serializer_cls = SERIALIZERS.get(serializer)
    if not serializer_cls:
        ctx.fail(
            f'Unknown serializer: {serializer} '
            '(use `seeqret serializers` to list available serializers).'
        )
    with cd(os.environ['SEEQRET']):
        seeqret.seeqret_transfer.export_secrets(
            to, FilterSpec(filter),
            serializer_cls, windows, linux
        )


@cli.command()
@click.pass_context
@click.option('-u', '--from-user', default='',
              help='Sender.')
@click.option('-f', '--file', default=None,
              help='Path to the vault file to export')
@click.option('-v', '--value', default=None,
              help='(string) value to export for the vault file')
@click.option('-s', '--serializer', default='json-crypt',
              help='Serializer to use (`seeqret serializers` to list).')
def save(ctx, from_user, file, value, serializer):
    """Save exported secrets.
    """
    serializer_cls = SERIALIZERS.get(serializer)
    if not serializer_cls:
        ctx.fail(
            f'Unknown serializer: {serializer} '
            '(use `seeqret serializers` to list available serializers).'
        )
    with cd(os.environ['SEEQRET']):
        seeqret.seeqret_transfer.import_secrets(
            from_user, file, value, serializer_cls
        )


@cli.command()
@click.pass_context
@click.argument(
    'dir',
    default='.',
    # prompt='Directory to initialize seeqret in',
)
@click.option(
    '--user',
    prompt=True,
    envvar='USERNAME',
    type=str,
    # default=lambda: f"{os.environ['USERDOMAIN']}\\{os.environ['USERNAME']}"
)
@click.option('--email', prompt=True)
@click.option('--pubkey', default=None, show_default=True)
@click.option('--key', default=None, show_default=True)
def init(ctx: click.Context,
         dir: str,
         user: str,
         email: str,
         pubkey: str | None = None,
         key: str | None = None):
    """Initialize a new vault
    """
    dirname = Path(dir).resolve()
    vault_dir = dirname / 'seeqret'

    # we want to create dirname / seeqret

    if not dirname.exists():
        # click.echo(f'The parent of the vault: {dirname} must exist.')
        ctx.fail(f'The parent of the vault: {dirname} must exist.')
        # return

    if not is_writable(dirname):
        # click.echo(f'The parent of the vault: {dirname} must be writable.')
        ctx.fail(f'The parent of the vault: {dirname} must be writable.')
        # return

    if vault_dir.exists():
        if not is_writable(vault_dir):
            ctx.fail(
                f'The vault: {vault_dir} exists and is not writeable, '
                'you must delete it manually.'
            )
            # return
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
@click.pass_context
@click.option('--url', prompt=True,
              help='URL that contains (only) the public key (as text)')
@click.option('--username', prompt=True,
              help='Username to record')
@click.option('--email', prompt=True,
              help='Email for the user')
def user(ctx, url, username, email):
    """Add a new user to the vault from a public key.

       If the public key is on GitHub, the url is the raw url, e.g.

       https://raw.githubusercontent.com/user/project/refs/heads/main/public.key
    """
    click.echo(f'Adding a new user, from {url}')
    with cd(os.environ['SEEQRET']):
        click.secho(f'Fetching public key: {url}', fg='blue')
        pubkey = seeqret_add.fetch_pubkey_from_url(url)
        seeqret_add.add_user(pubkey, username, email)


@cli.command()
@click.pass_context
@click.argument('url')
def fetch(ctx, url):
    "Debugging"
    # XXX: remove me, for debugging...
    seeqret_add.fetch_pubkey_from_url(url)


@add.command()
@click.argument('name')
@click.argument('value')
@click.option('--app', default='*', show_default=True,
              help='The app to add the secret to')
@click.option('--env', default='*', show_default=True,
              help='The env(ironment) to add the secret to (e.g. dev/prod)')
def key(name: str, value: str, app: str = None, env: str = None):
    """Add a new NAME -> VALUE mapping.

       You can (should) specify the app and environment properties when adding
       a new mapping.
    """
    print("KEY::")
    click.echo(
        f'Adding a new key: {name}, value: {value}, app: {app}, env: {env}'
    )

    with cd(os.environ['SEEQRET']):
        print("CALLING:seeqret_add.add_key", name, value, app, env)
        seeqret_add.add_key(name, value, app, env)
