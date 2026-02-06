import json
import os
import re
from pathlib import Path

import click
from click import Context

from . import __version__
from .storage.sqlite_storage import SqliteStorage
from .seeqret_transfer import export_secrets, import_secrets
from .seeqret_init import secrets_init, upgrade_db
from .seeqret_add import add_user
from .run_utils import seeqret_dir, is_initialized, current_user
from .console_utils import as_table, dochelp
from .fileutils import is_writable, read_binary_file
from .filterspec import FilterSpec
from .serializers.serializer import SERIALIZERS
from .cli_group_rm import key as rm_key
from .cli_group_add import key as add_key, text as add_text
from .cli_group_server import init as server_init
import logging


def parse_version(version_str: str) -> tuple:
    """Parse a version string into a tuple of integers for comparison."""
    parts = version_str.strip().split('.')
    result = []
    for part in parts:
        # Extract leading digits only (handles cases like "3a" -> 3)
        match = re.match(r'(\d+)', part)
        if match:
            result.append(int(match.group(1)))
        else:
            result.append(0)
    return tuple(result)


def check_version_requirement(requirement: str, current: str) -> tuple[bool, str]:
    """Check if current version meets the requirement.

    Args:
        requirement: Version requirement string (e.g., ">=0.3", ">0.2.2", "==0.3")
        current: Current version string

    Returns:
        Tuple of (meets_requirement, operator_used)
    """
    requirement = requirement.strip()

    if requirement.startswith('>='):
        op, required = '>=', requirement[2:]
        return parse_version(current) >= parse_version(required), op
    elif requirement.startswith('<='):
        op, required = '<=', requirement[2:]
        return parse_version(current) <= parse_version(required), op
    elif requirement.startswith('=='):
        op, required = '==', requirement[2:]
        return parse_version(current) == parse_version(required), op
    elif requirement.startswith('!='):
        op, required = '!=', requirement[2:]
        return parse_version(current) != parse_version(required), op
    elif requirement.startswith('>'):
        op, required = '>', requirement[1:]
        return parse_version(current) > parse_version(required), op
    elif requirement.startswith('<'):
        op, required = '<', requirement[1:]
        return parse_version(current) < parse_version(required), op
    else:
        # Default to >= if no operator
        return parse_version(current) >= parse_version(requirement), '>='


def parse_env_template_version(first_line: str) -> str | None:
    """Parse version requirement from env.template first line.

    Expected format: @seeqret>=0.3 or @seeqret>0.2.2

    Returns:
        Version requirement string (e.g., ">=0.3") or None if not found
    """
    first_line = first_line.strip()
    match = re.match(r'^@seeqret\s*([><=!]+\s*[\d.]+)', first_line, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


DIRNAME = Path(__file__).parent
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def validate_current_user():
    user = current_user()
    with seeqret_dir():
        storage = SqliteStorage()
        # print("CURRENT USER:", user)
        # print("USERS:", storage.fetch_users(username=user))
        if not storage.fetch_users(username=user):
            click.secho("You are not a valid user of this vault", fg='red')
            return False
    return True


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option()
@click.pass_context
@click.option('-L', '--log', default="ERROR")
def cli(ctx, log):
    logging.basicConfig(level=getattr(logging, log))
    ctx.obj = {
        "seeqrets_dir": os.environ.get("SEEQRETS"),
        "curdir": os.getcwd(),
    }
    if is_initialized():
        if not validate_current_user():
            ctx.fail("You are not a valid user of this vault")


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
    with seeqret_dir():
        upgrade_db()


@cli.command()
@click.option('-f', '--filter', default='*', show_default=True,
              help='filterspec (see https://thebjorn.github.io/seeqret/filter-strings/)')
def list(filter):
    """List the contents of the vault
    """
    with seeqret_dir():
        storage = SqliteStorage()
        fspec = FilterSpec(filter)
        secrets = storage.fetch_secrets(**fspec.to_filterdict())
        if not secrets:
            click.secho("No matching secrets found.")
            return
        as_table("App,Env,Key,Value,Type", secrets)


@cli.command()
@click.pass_context
@click.argument('filter')
def get(ctx, filter):
    """Get the value of a secret (specified by FILTER).
    """
    with seeqret_dir():
        storage = SqliteStorage()
        fspec = FilterSpec(filter)
        secrets = storage.fetch_secrets(**fspec.to_filterdict())
        if len(secrets) > 1:
            ctx.fail(f"Found {len(secrets)} secrets for {filter}")
        if not secrets:
            ctx.fail(f"No secrets found for {filter}")
        secret = secrets[0]
        click.echo(secret.value)


@cli.command()
def owner():
    """List the owner of the vault
    """
    with seeqret_dir():
        storage = SqliteStorage()
        as_table('username,email,publickey',
                 [storage.fetch_admin()])


@cli.command()
def whoami():
    """Display the current user and their role in the vault.
    """
    user = current_user()
    with seeqret_dir():
        storage = SqliteStorage()
        admin = storage.fetch_admin()
        if admin and admin.username == user:
            click.echo(f"{user} (owner)")
        elif storage.fetch_users(username=user):
            click.echo(f"{user}")
        else:
            click.echo(f"{user} (not a registered user of this vault)")


@cli.command()
@click.option('--export', is_flag=True, help='Export the users for import into another vault')
def users(export):
    """List the users in the vault
    """
    # print("SEEQRET:DIR:", os.environ['SEEQRET'])
    with seeqret_dir():
        storage = SqliteStorage()
        users = storage.fetch_users()
        if export:
            for user in users:
                click.echo(f"seeqret add user --username {user.username} --email {user.email} --pubkey {user.pubkey}")  # noqa
        else:
            as_table('username,email,publickey', users)


@cli.command()
def keys():
    """List the admins keys.
    """
    with seeqret_dir():
        private_key = read_binary_file('private.key').decode('ascii')
        public_key = read_binary_file('public.key').decode('ascii')
        as_table('private_key,public_key',
                 [[private_key, public_key]])


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
def env(ctx):
    """Read filters from env.template and export values from the vault to an .env file.

    The env.template file uses the following format:

    \b
    Lines:
      # comment           Comment lines (ignored)
      @seeqret>=VERSION   Version requirement (e.g. @seeqret>=0.3)
      FILTER              A filter specifying which secrets to include

    \b
    Filter format (fields separated by colons):
      KEY                 Match a specific key (any app/env)
      APP:ENV             Match all keys for app/environment
      APP:ENV:KEY         Match a specific app, environment, and key

    \b
    Rename syntax (write secret to .env under a different name):
      OUTPUT_NAME=FILTER  Fetch secret matching FILTER, output as OUTPUT_NAME

    \b
    Glob patterns (* and ?) are supported in all fields.
    Empty fields default to * (match all).

    \b
    Examples of env.template:
      @seeqret>=0.3
      # Database credentials
      myapp:prod:DB_*
      myapp:prod:SECRET_KEY
      :dev:
      # Rename: fetch FOO from local env, write as LOCAL_FOO
      LOCAL_FOO=:local:FOO
    """
    if not os.path.exists('env.template'):
        click.secho("Error: No env.template file found in the current directory.", fg='red')
        click.echo("\nCreate an env.template file to specify which secrets to export.")
        click.echo("See 'seeqret env --help' for format details.")
        ctx.exit(1)
        return

    with open('env.template', 'r') as f:
        lines = f.readlines()

    # Check for version requirement in first line
    if lines:
        version_req = parse_env_template_version(lines[0])
        if version_req:
            meets_req, op = check_version_requirement(version_req, __version__)
            if not meets_req:
                click.secho(
                    f"Error: env.template requires seeqret{version_req}, "
                    f"but you have version {__version__}",
                    fg='red'
                )
                click.echo("\nTo upgrade seeqret, run:")
                click.secho("    pip install --upgrade seeqret", fg='blue')
                ctx.exit(1)

    # Validate @ directives
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('@') and not parse_env_template_version(stripped):
            click.secho(
                f"Error: Invalid directive on line {i}: {stripped}",
                fg='red'
            )
            click.echo("\nExpected format: @seeqret>=VERSION")
            click.echo("Examples: @seeqret>=0.3  @seeqret>0.2.2  @seeqret==1.0")
            ctx.exit(1)

    # Parse filter lines, supporting rename syntax: OUTPUT_NAME=FILTER
    filters = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or stripped.startswith('@'):
            continue
        if '=' in stripped:
            output_name, _, filter_string = stripped.partition('=')
            filters.append((output_name, FilterSpec(filter_string)))
        else:
            filters.append((None, FilterSpec(stripped)))

    envserializer = SERIALIZERS['env']()
    curdir = os.getcwd()
    with seeqret_dir():
        storage = SqliteStorage()

        errors = 0
        secrets = []
        keys = set()
        for output_name, fspec in filters:
            for secret in storage.fetch_secrets(**fspec.to_filterdict()):
                if output_name:
                    secret.key = output_name
                if secret.key not in keys:
                    secrets.append(secret)
                    keys.add(secret.key)
                else:
                    click.secho(f"Duplicate key: {secret.key}", fg='red')
                    errors += 1
        if errors:
            click.secho(f"\nFound {errors} duplicate keys (not creating .env file)", bg='red', fg='bright_yellow')  # noqa
            return

        # as_table('app,env,key,value,type', secrets)
        res = envserializer.dumps(secrets, False)
        print(res)
        print()

        try:
            curdir = ctx.obj['curdir']
        except:  # noqa
            pass

        with open(os.path.join(curdir, '.env'), 'w') as f:
            f.write(res)
        click.secho(f"\nCreated .env file with {len(secrets)} secrets", fg='green')


def parse_env_line(line: str) -> tuple[str, str] | None:
    """Parse a single line from a .env file.

    Handles formats:
        KEY=value
        KEY="value"
        KEY='value'
        export KEY=value

    Returns:
        Tuple of (key, value) or None if line is empty/comment
    """
    line = line.strip()

    # Skip empty lines and comments
    if not line or line.startswith('#'):
        return None

    # Handle 'export KEY=value' format
    if line.startswith('export '):
        line = line[7:].strip()

    # Find the = separator
    if '=' not in line:
        return None

    key, _, value = line.partition('=')
    key = key.strip()
    value = value.strip()

    # Remove surrounding quotes if present
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]

    if not key:
        return None

    return key, value


@cli.command()
@click.pass_context
@click.argument('filename', type=click.Path(exists=True))
@click.option('--app', default='*', show_default=True,
              help='The app to add the secrets to')
@click.option('--env', default='*', show_default=True,
              help='The environment to add the secrets to (e.g. dev/prod)')
@click.option('--update', is_flag=True,
              help='Update existing secrets instead of skipping them')
@click.option('--dry-run', is_flag=True,
              help='Show what would be imported without making changes')
def importenv(ctx, filename, app, env, update, dry_run):
    """Import secrets from a .env file.

    Example:
        seeqret importenv .env.example --app=myapp --env=dev
    """
    from .models import Secret

    # Parse the .env file
    with open(filename, 'r') as f:
        lines = f.readlines()

    parsed = []
    for i, line in enumerate(lines, 1):
        result = parse_env_line(line)
        if result:
            key, value = result
            if ':' in key:
                click.secho(f"Warning: Skipping line {i}, colon not allowed in key: {key}",
                            fg='yellow')
                continue
            parsed.append((key, value))

    if not parsed:
        click.secho("No secrets found in file", fg='yellow')
        return

    click.echo(f"Found {len(parsed)} secrets in {filename}")

    if dry_run:
        click.echo("\nDry run - would import:")
        for key, value in parsed:
            display_value = value[:20] + '...' if len(value) > 20 else value
            click.echo(f"  {app}:{env}:{key} = {display_value}")
        return

    with seeqret_dir():
        storage = SqliteStorage()
        added = 0
        updated = 0
        skipped = 0

        for key, value in parsed:
            # Check if secret already exists
            existing = storage.fetch_secrets(app=app, env=env, key=key)

            if existing:
                if update:
                    existing[0].value = value
                    storage.update_secret(existing[0])
                    updated += 1
                    click.secho(f"  Updated: {key}", fg='blue')
                else:
                    skipped += 1
                    click.secho(f"  Skipped (exists): {key}", fg='yellow')
            else:
                secret = Secret(
                    app=app,
                    env=env,
                    key=key,
                    plaintext_value=value,
                    type='str'
                )
                storage.add_secret(secret)
                added += 1
                click.secho(f"  Added: {key}", fg='green')

        click.echo()
        click.secho(f"Import complete: {added} added, {updated} updated, {skipped} skipped",
                    fg='green')


@cli.command()
@click.pass_context
def backup(ctx):
    """Backup the vault to a file.
    """
    serializer = SERIALIZERS['backup']
    with seeqret_dir():
        export_secrets(
            ctx, to='self', fspec=FilterSpec('::'),
            serializer=serializer, out=False, windows=False, linux=False
        )


@cli.command()
@click.pass_context
@click.option('--to', multiple=True, required=True,
              help='User(s) to export to (can be used multiple times)'
                   ' the user(s) must exist in the vault.')
@click.option('-f', '--filter', default=[], show_default=True, multiple=True,
              help='A seeqret filter string (can be used multiple times)')
@click.option(
    '-s', '--serializer', default='json-crypt', show_default=True,
    help='Name of serializer to use (`seeqret serializers` to list).')
@click.option('-o', '--out', default=None, show_default=True,
              help='Output file (default: stdout).')
@click.option('-w', '--windows', default=False, is_flag=True,
              help='Export to windows format.')
@click.option('-l', '--linux', default=False, is_flag=True,
              help='Export to linux format.')
def export(ctx, to, filter, serializer='json-crypt', out=None,
           windows=False, linux=False):
    """Export the vault TO a user (use `seeqret load` to import)

       Example:

       seeqret export --to u1 --to u2 --f :app1::FOO* --f :app1::BAR* --s command

       This will export all secrets starting with FOO or BAR from app1
       to users u1 and u2.
    """
    serializer_cls = SERIALIZERS.get(serializer)
    if not serializer_cls:
        ctx.fail(
            f'Unknown serializer: `{serializer}` ({", ".join(SERIALIZERS.keys())}) '
            '(use `seeqret serializers` to list available serializers).'
        )

    with seeqret_dir():
        storage = SqliteStorage()
        for user in to:
            if user != 'self' and not storage.fetch_users(username=user):
                ctx.fail(f"User {user} does not exist in the vault")
            print(f"\nSeeqrets for {user}:")
            for fspec in filter:
                export_secrets(
                    ctx,
                    to=user, fspec=FilterSpec(fspec),
                    serializer=serializer_cls, out=out, windows=windows, linux=linux
                )


@cli.command()
def introduction():
    """Print an introduction to the vault.
    """
    click.echo("Please add me to your vault!\n")

    with seeqret_dir():
        storage = SqliteStorage()
        self = storage.fetch_users(username=current_user())[0]
        click.echo(f"seeqret add user --username {self.username} --email {self.email} --pubkey {self.pubkey}")  # noqa


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
    with seeqret_dir():
        import_secrets(
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
    """Initialize a new vault in DIR
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

    secrets_init(dirname, user, email, pubkey, key)


@cli.group()
def server():
    """Server commands."""
    pass


server.add_command(server_init)


# @cli.command()
# @click.pass_context
# @click.argument('url')
# def fetch(ctx, url):
#     "Debugging"
#     # XXX: remove me, for debugging...
#     seeqret_add.fetch_pubkey_from_url(url)


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
@click.argument('value')
@click.option('--all', is_flag=True, help='Update all matching secrets without prompting')
def value(ctx, filter: str, value: str, all: bool):
    """Update secrets matching FILTER to the new VALUE.

    FILTER is a seeqret filter string in the format [app]:[env]:[key].
    Use * or leave empty for wildcards. Examples:
        myapp:dev:DB_PASS    - specific secret
        myapp:dev:           - all secrets in myapp/dev
        ::API_KEY            - API_KEY in any app/env

    VALUE is the new plaintext value for the secret(s).

    If multiple secrets match, you'll be prompted unless --all is used.

    Examples:
        seeqret edit value myapp:dev:DB_PASSWORD newsecret123
        seeqret edit value "::API_*" newkey --all
    """
    with seeqret_dir():
        storage = SqliteStorage()
        fspec = FilterSpec(filter)
        secrets = storage.fetch_secrets(**fspec.to_filterdict())
        if not secrets:
            ctx.fail(f'No secrets found for {filter}')
        if len(secrets) > 1:
            if not all:
                as_table('app,env,key,value,type', secrets)
                if not click.confirm("Update all values?"):
                    ctx.fail('Aborted')
        for secret in secrets:
            secret.value = value
            storage.update_secret(secret)

        click.secho(f"updated {pluralize(secrets, 'secret', 'secrets')}", fg='green')
        as_table('app,env,key,value,type', secrets)


@cli.group()
def add():
    """Add a new secret.
    """
    pass


add.add_command(add_key)
add.add_command(add_text)


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
    """
    click.secho(f'Adding a new user {username}|{email}|{pubkey}', fg='blue')
    with seeqret_dir():
        # click.secho(f'Fetching public key: {url}', fg='blue')
        # pubkey = seeqret_add.fetch_pubkey_from_url(url)
        add_user(pubkey, username, email)
