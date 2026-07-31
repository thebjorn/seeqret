"""Dynamic ssh push/verify commands resolved from the remotes table.

   ``seeqret push <alias> <filterspec>`` and
   ``seeqret verify <alias> <filterspec>`` are not statically defined:
   the ``push`` and ``verify`` click groups resolve unknown subcommand
   names against the vault's ``remotes`` table and build the command on
   the fly. The remote's command templates (``set_cmd``/``get_cmd``)
   describe what to run on the host, so seeqret has no intrinsic
   knowledge of private server-side tools like dkpw.
"""

import shlex
import subprocess

import click

from .filterspec import FilterSpec
from .models import Remote
from .run_utils import seeqret_dir
from .storage.sqlite_storage import SqliteStorage


def _load_remote(alias: str) -> Remote | None:
    """Look up an alias in the vault; None when it (or the vault
       itself) does not exist -- group dispatch must never crash on
       e.g. ``seeqret push --help`` outside a vault.
    """
    try:
        with seeqret_dir():
            return SqliteStorage().fetch_remote(alias)
    except Exception:
        return None


def _load_remote_aliases() -> list[str]:
    try:
        with seeqret_dir():
            return [r.alias for r in SqliteStorage().fetch_remotes()]
    except Exception:
        return []


def _render_cmd(template: str, key: str, value: str = None) -> str:
    """Substitute {key}/{value} placeholders, shell-quoted for the
       remote (POSIX) shell. Templates must not add their own quotes.
    """
    cmd = template.replace('{key}', shlex.quote(key))
    if value is not None:
        cmd = cmd.replace('{value}', shlex.quote(value))
    return cmd


def _ssh_run(remote: Remote, remote_cmd: str, input: str = None):
    return subprocess.run(
        ['ssh', remote.userhost, remote_cmd],
        input=input, capture_output=True, text=True,
    )


def _fetch_filtered_secrets(ctx, filterspec: str, filter_: str):
    """Fetch vault secrets for the effective filter, with the same
       no-match and duplicate-key guards as ``push vercel``.
    """
    effective_filter = filter_ or filterspec or '*'

    with seeqret_dir():
        storage = SqliteStorage()
        fspec = FilterSpec(effective_filter)
        secrets = storage.fetch_secrets(**fspec.to_filterdict())

    if not secrets:
        ctx.fail(f"No secrets found for {effective_filter}")

    keys = {}
    for secret in secrets:
        if secret.key in keys:
            ctx.fail(
                f"Duplicate key: {secret.key} "
                f"(found in {keys[secret.key]} and "
                f"{secret.app}:{secret.env})"
            )
        keys[secret.key] = f"{secret.app}:{secret.env}"

    return secrets


def make_push_command(remote: Remote) -> click.Command:
    """Build a ``seeqret push <alias>`` command for an ssh remote.
    """
    @click.command(remote.alias)
    @click.pass_context
    @click.argument('filterspec', default='')
    @click.option('-f', '--filter', 'filter_', default='',
                  show_default=False,
                  help='filterspec (see https://thebjorn.github.io/seeqret/filter-strings/)')
    @click.option('--dry-run', is_flag=True,
                  help='Show what would be pushed without making changes.')
    def push_remote(ctx, filterspec, filter_, dry_run):
        secrets = _fetch_filtered_secrets(ctx, filterspec, filter_)

        click.echo(
            f"Pushing {len(secrets)} secret(s) to "
            f"{remote.alias} ({remote.userhost})..."
        )

        if dry_run:
            # Mask any command-line value: unlike the real invocation,
            # dry-run output must never contain the secret. In stdin
            # mode the command carries no value, so it prints as-is.
            for secret in secrets:
                cmd = _render_cmd(remote.set_cmd, secret.key, '*****')
                suffix = '  (value on stdin)' \
                    if remote.value_via_stdin else ''
                click.echo(f"  would push {secret.key}")
                click.echo(f'    ssh {remote.userhost} "{cmd}"{suffix}')
            return

        pushed = 0
        failed = 0
        for secret in secrets:
            cmd = _render_cmd(remote.set_cmd, secret.key, secret.value)
            res = _ssh_run(
                remote, cmd,
                input=secret.value if remote.value_via_stdin else None,
            )
            if res.returncode == 0:
                click.secho(f"  pushed {secret.key}", fg='green')
                pushed += 1
            else:
                err = (res.stderr or res.stdout).strip()
                click.secho(f"  FAILED {secret.key}: {err}", fg='red')
                failed += 1

        click.echo()
        if failed:
            click.secho(
                f"Pushed {pushed}, failed {failed}.",
                fg='yellow' if pushed else 'red',
            )
            ctx.exit(1)
        else:
            click.secho(
                f"Pushed {pushed} secret(s) to {remote.alias}.",
                fg='green',
            )

    push_remote.help = (
        f"Push secrets matching FILTER to {remote.userhost} over ssh."
    )
    return push_remote


def make_verify_command(remote: Remote) -> click.Command:
    """Build a ``seeqret verify <alias>`` command for an ssh remote.
    """
    @click.command(remote.alias)
    @click.pass_context
    @click.argument('filterspec', default='')
    @click.option('-f', '--filter', 'filter_', default='',
                  show_default=False,
                  help='filterspec (see https://thebjorn.github.io/seeqret/filter-strings/)')
    def verify_remote(ctx, filterspec, filter_):
        if not remote.get_cmd:
            ctx.fail(
                f"Remote '{remote.alias}' has no get command, so it "
                "cannot be verified. Re-add it with a --get template."
            )

        secrets = _fetch_filtered_secrets(ctx, filterspec, filter_)

        click.echo(
            f"Verifying {len(secrets)} secret(s) against "
            f"{remote.alias} ({remote.userhost})..."
        )

        ok = 0
        failed = 0
        for secret in secrets:
            cmd = _render_cmd(remote.get_cmd, secret.key)
            res = _ssh_run(remote, cmd)
            if res.returncode != 0:
                click.secho(f"  MISSING  {secret.key}", fg='red')
                failed += 1
            elif res.stdout.strip() == secret.value:
                click.secho(f"  ok       {secret.key}", fg='green')
                ok += 1
            else:
                click.secho(f"  MISMATCH {secret.key}", fg='red')
                failed += 1

        click.echo()
        if failed:
            click.secho(
                f"Verified {ok}, failed {failed}.",
                fg='yellow' if ok else 'red',
            )
            ctx.exit(1)
        else:
            click.secho(
                f"Verified {ok} secret(s) against {remote.alias}.",
                fg='green',
            )

    verify_remote.help = (
        f"Verify secrets matching FILTER against {remote.userhost} "
        "over ssh."
    )
    return verify_remote


class RemoteDispatchGroup(click.Group):
    """A click group that falls back to ssh remote aliases.

       Static subcommands (e.g. ``vercel``) win; any other name is
       looked up in the vault's remotes table and materialized via
       ``command_factory``.
    """
    command_factory = None

    def get_command(self, ctx, cmd_name):
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd
        remote = _load_remote(cmd_name)
        if remote is None:
            return None
        return type(self).command_factory(remote)

    def list_commands(self, ctx):
        names = set(super().list_commands(ctx))
        names.update(_load_remote_aliases())
        return sorted(names)


class PushGroup(RemoteDispatchGroup):
    command_factory = staticmethod(make_push_command)


class VerifyGroup(RemoteDispatchGroup):
    command_factory = staticmethod(make_verify_command)
