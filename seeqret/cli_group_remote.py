"""Click command group for ``seeqret remote ...``.

   Manage ssh remote targets: named hosts that secrets can be pushed
   to (``seeqret push <alias>``) and verified against
   (``seeqret verify <alias>``).
"""

import click

from .models import Remote
from .run_utils import seeqret_dir
from .storage.sqlite_storage import SqliteStorage


def _parse_userhost(ctx, userhost: str) -> tuple[str, str]:
    username, sep, hostname = userhost.partition('@')
    if not sep or not username or not hostname:
        ctx.fail(
            f"Expected USER@HOST (e.g. myuser@myhost.example.com), "
            f"got: {userhost}"
        )
    return username, hostname


@click.group('remote')
def remote():
    """Manage ssh remote targets for push/verify."""
    pass


@remote.command('add')
@click.pass_context
@click.argument('alias')
@click.argument('userhost')
@click.option('--set', 'set_cmd', required=True,
              help='Remote command template to set a secret. '
                   '{key} and {value} are substituted shell-quoted, '
                   'so do not add your own quotes around them. '
                   'Without a {value} placeholder the value is piped '
                   'on stdin instead (preferred: it keeps the secret '
                   'out of the remote command line).')
@click.option('--get', 'get_cmd', default=None,
              help='Remote command template to fetch a secret value '
                   '(prints the value on stdout). {key} is substituted '
                   'shell-quoted. Omit for a push-only remote.')
def add(ctx, alias, userhost, set_cmd, get_cmd):
    """Add (or update) an ssh remote named ALIAS at USERHOST.

    \b
    Example:
        seeqret remote add myhost myuser@myhost.example.com \\
            --set "source /srv/venv/myvenv/bin/activate && myvault set-secret --key {key} --stdin" \\
            --get "... myvault get-secret --key {key} --stdout"

    Afterwards `seeqret push myhost myapp:prod:FOO` runs the set
    command on the host over ssh for each matching secret (piping the
    value on stdin, since the template has no {value} placeholder),
    and `seeqret verify myhost myapp:prod:FOO` compares the get
    command's output to the vault value.
    """
    username, hostname = _parse_userhost(ctx, userhost)

    if '{key}' not in set_cmd:
        ctx.fail("--set template must contain {key}")
    if get_cmd is not None and '{key}' not in get_cmd:
        ctx.fail("--get template must contain {key}")

    rmt = Remote(
        alias=alias,
        username=username,
        hostname=hostname,
        set_cmd=set_cmd,
        get_cmd=get_cmd,
    )
    with seeqret_dir():
        try:
            SqliteStorage().upsert_remote(rmt)
        except RuntimeError as e:
            ctx.fail(str(e))

    click.secho(f"Added remote {alias} ({rmt.userhost})", fg='green')
    if rmt.value_via_stdin:
        click.echo("Values will be piped on stdin "
                   "(no {value} placeholder in --set).")
    else:
        click.echo("Values will be passed on the remote command line "
                   "({value} placeholder in --set).")


@remote.command('list')
def list_remotes():
    """List the registered ssh remotes."""
    with seeqret_dir():
        remotes = SqliteStorage().fetch_remotes()

    if not remotes:
        click.echo("No remotes registered "
                   "(use `seeqret remote add` to add one).")
        return

    for rmt in remotes:
        click.secho(f"{rmt.alias}", fg='cyan', nl=False)
        click.echo(f"  {rmt.userhost}")
        click.echo(f"    set: {rmt.set_cmd}")
        if rmt.get_cmd:
            click.echo(f"    get: {rmt.get_cmd}")
        else:
            click.echo("    get: (none -- push only)")


@remote.command('rm')
@click.pass_context
@click.argument('alias')
def rm(ctx, alias):
    """Remove the ssh remote named ALIAS."""
    with seeqret_dir():
        deleted = SqliteStorage().remove_remote(alias)

    if not deleted:
        ctx.fail(f"No remote named {alias}")
    click.secho(f"Removed remote {alias}", fg='green')
