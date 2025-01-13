import json
import os
from pathlib import Path

import click
from click import Context
from .storage.sqlite_storage import SqliteStorage
from . import seeqret_transfer
# from .context import Context
from . import seeqret_init, seeqret_add, cd
from .console_utils import as_table, dochelp
from .fileutils import is_writable
from .filterspec import FilterSpec
from .serializers.serializer import SERIALIZERS
from .cli_group_rm import key as rm_key
from .cli_group_add import file as add_file, key as add_key
import logging

DIRNAME = Path(__file__).parent
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@click.option('-L', '--log', default="ERROR")
def cli(ctx, log):
    logging.basicConfig(level=getattr(logging, log))
    ctx.obj = {
        "seeqrets_dir": os.environ.get("SEEQRETS"),
        "curdir": os.getcwd(),
    }


@cli.command()
@click.option('-d', '--dump', is_flag=True, help='Dump the info')
def info(dump):
    """List hierarchical command structure.
    """
    with Context(cli) as ctx:
        info = ctx.to_info_dict()
        if dump:
            print(json.dumps(info, indent=4))
            return

    def _help(command):
        txt = command.get('help', '') or ''
        return txt.split('\n')[0]

    def _print_command_info(command, indent=0):
        # print(json.dumps(command)[:80])
        name = '    ' * indent + command['name']
        help = _help(command)
        print(f"{name:30} {help}")
        if 'commands' in command:
            for subcommand in command['commands'].values():
                _print_command_info(subcommand, indent + 1)

    _print_command_info(info['command'])


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
        storage = SqliteStorage()
        fspec = FilterSpec(filter)
        as_table("App,Env,Key,Value,Type",
                 storage.fetch_secrets(**fspec.to_filterdict()))


@cli.command()
def users():
    """List the users in the vault
    """
    # print("SEEQRET:DIR:", os.environ['SEEQRET'])
    with cd(os.environ['SEEQRET']):
        storage = SqliteStorage()
        as_table('username,email,publickey',
                 storage.fetch_users())


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
def backup():
    """Backup the vault to a file.
    """
    serializer = SERIALIZERS['backup']
    with cd(os.environ['SEEQRET']):
        seeqret_transfer.export_secrets(
            'self', FilterSpec('::'),
            serializer, False, False
        )


@cli.command()
@click.pass_context
@click.argument('to')
@click.option('-f', '--filter', default='',
              help='A seeqret filter string (see XXX) ')
@click.option(
    '-s', '--serializer', default='json-crypt',
    help='Name of serializer to use (`seeqret serializers` to list).')
@click.option('-o', '--out', default=None,
              help='Output file (default: stdout).')
@click.option('-w', '--windows', default=False, is_flag=True,
              help='Export to windows format.')
@click.option('-l', '--linux', default=False, is_flag=True,
              help='Export to linux format.')
def export(ctx, to, filter, serializer='json-crypt', out=None,
           windows=False, linux=False):
    """Export the vault to a user (use `seeqret load` to import)
    """
    serializer_cls = SERIALIZERS.get(serializer)
    if not serializer_cls:
        ctx.fail(
            f'Unknown serializer: `{serializer}` ({", ".join(SERIALIZERS.keys())}) '
            '(use `seeqret serializers` to list available serializers).'
        )
    with cd(os.environ['SEEQRET']):
        seeqret_transfer.export_secrets(
            ctx,
            to, FilterSpec(filter),
            serializer_cls, out, windows, linux
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
def load(ctx, from_user, file, value, serializer):
    """Save exported secrets to local vault.
    """
    serializer_cls = SERIALIZERS.get(serializer)
    if not serializer_cls:
        ctx.fail(
            f'Unknown serializer: {serializer} '
            '(use `seeqret serializers` to list available serializers).'
        )
    with cd(os.environ['SEEQRET']):
        seeqret_transfer.import_secrets(
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


@cli.command()
@click.pass_context
@click.argument('url')
def fetch(ctx, url):
    "Debugging"
    # XXX: remove me, for debugging...
    seeqret_add.fetch_pubkey_from_url(url)


@cli.group()
def rm():
    """Remove a secret or user from the vault.
    """
    pass


rm.add_command(rm_key)


@cli.group()
def edit():
    """Edit a secret or user in the vault.
    """


def pluralize(items, word, plural):
    return word if len(items) == 1 else plural


@edit.command()
@click.pass_context
@click.argument('filter', default='::')
@click.argument('val')
def value(ctx, filter: str, val: str):
    with cd(os.environ['SEEQRET']):
        storage = SqliteStorage()
        fspec = FilterSpec(filter)
        secrets = storage.fetch_secrets(**fspec.to_filterdict())
        if not secrets:
            ctx.fail(f'No secrets found for {filter}')
        if len(secrets) > 1:
            as_table('app,env,key,value,type', secrets)
            if not click.confirm("Update all values?"):
                ctx.fail('Aborted')
        for secret in secrets:
            secret.value = val
            storage.update_secret(secret)

        click.secho(f"updated {pluralize(secrets, 'secret', 'secrets')}", fg='green')
        as_table('app,env,key,value,type', secrets)


@cli.group()
def add():
    """Add a new secret, key or user
    """
    pass


add.add_command(add_key)
add.add_command(add_file)


@add.command()
@click.pass_context
@click.option('--username', prompt=True,
              help='Username to record')
@click.option('--email', prompt=True,
              help='Email for the user')
@click.option('--pubkey', prompt=True,
              help='Public key for the user')
def user(ctx, username, email, pubkey):
    """Add a new user to the vault from a public key.

       If the public key is on GitHub, the url is the raw url, e.g.

       https://raw.githubusercontent.com/user/project/refs/heads/main/public.key
    """
    click.secho(f'Adding a new user {username}|{email}|{pubkey}', fg='blue')
    with cd(os.environ['SEEQRET']):
        # click.secho(f'Fetching public key: {url}', fg='blue')
        # pubkey = seeqret_add.fetch_pubkey_from_url(url)
        seeqret_add.add_user(pubkey, username, email)
