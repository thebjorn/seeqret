"""Click command group for ``seeqret push ...``.

   Push secrets from the local vault out to external systems
   (currently: Vercel projects via the ``vercel`` CLI).
"""

import os
import shutil
import subprocess

import click

from .filterspec import FilterSpec
from .run_utils import seeqret_dir
from .storage.sqlite_storage import SqliteStorage


VERCEL_TARGETS = ('production', 'preview', 'development')


def _check_vercel_linked(ctx, curdir) -> str:
    """Verify ``vercel`` is on PATH and the current dir is a linked project.

       Returns the resolved path to the ``vercel`` executable. On
       Windows ``vercel`` is typically a ``.cmd`` shim, and
       ``subprocess.run`` (without ``shell=True``) cannot resolve
       PATHEXT, so callers must use the resolved path.
    """
    vercel_exe = shutil.which('vercel')
    if not vercel_exe:
        ctx.fail(
            "The `vercel` CLI was not found on PATH. "
            "Install it from https://vercel.com/docs/cli and try again."
        )

    project_file = os.path.join(curdir, '.vercel', 'project.json')
    if not os.path.exists(project_file):
        ctx.fail(
            f"No linked Vercel project found in {curdir} "
            "(missing .vercel/project.json). Run `vercel link` first."
        )
    return vercel_exe


def _parse_targets(target: str) -> list[str]:
    targets = [t.strip() for t in target.split(',') if t.strip()]
    unknown = [t for t in targets if t not in VERCEL_TARGETS]
    if unknown:
        raise click.ClickException(
            f"Unknown Vercel target(s): {', '.join(unknown)}. "
            f"Valid choices: {', '.join(VERCEL_TARGETS)}."
        )
    return targets


def _push_one(vercel_exe: str, key: str, value: str,
              targets: list[str], cwd: str) -> tuple[bool, str]:
    """Push a single secret to Vercel, overwriting any existing value.

       Returns (ok, message). ``vercel env add`` and ``vercel env rm``
       accept exactly one environment per invocation, so we loop per
       target. The ``rm`` step is best-effort (the variable may not
       exist yet); failures are ignored.
    """
    for tgt in targets:
        subprocess.run(
            [vercel_exe, 'env', 'rm', key, tgt, '--yes'],
            capture_output=True, text=True, cwd=cwd,
        )

        add = subprocess.run(
            [vercel_exe, 'env', 'add', key, tgt],
            input=value, capture_output=True, text=True, cwd=cwd,
        )
        if add.returncode != 0:
            err = (add.stderr or add.stdout).strip()
            return False, f"{tgt}: {err}"
    return True, ''


@click.group('push')
def push():
    """Push secrets from the vault to external systems."""
    pass


@push.command('vercel')
@click.pass_context
@click.argument('filterspec', default='')
@click.option('-f', '--filter', 'filter_', default='', show_default=False,
              help='filterspec (see https://thebjorn.github.io/seeqret/filter-strings/)')
@click.option('--target', default=','.join(VERCEL_TARGETS), show_default=True,
              help='Comma-separated Vercel environments to push to '
                   '(production, preview, development).')
@click.option('--dry-run', is_flag=True,
              help='Show what would be pushed without making changes.')
def vercel(ctx, filterspec, filter_, target, dry_run):
    """Push secrets matching FILTER to the linked Vercel project.

    The Vercel CLI must be installed and the current directory must be
    a linked project (run `vercel link` first). Existing variables with
    the same name on the chosen targets are overwritten.

    \b
    Examples:
        seeqret push vercel myapp:prod:*
        seeqret push vercel --filter myapp:prod:DB_*
        seeqret push vercel myapp:prod:* --target production
        seeqret push vercel myapp:prod:* --dry-run
    """
    effective_filter = filter_ or filterspec or '*'
    curdir = ctx.obj.get('curdir') if ctx.obj else os.getcwd()
    curdir = curdir or os.getcwd()

    targets = _parse_targets(target)

    vercel_exe = None
    if not dry_run:
        vercel_exe = _check_vercel_linked(ctx, curdir)

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

    click.echo(
        f"Pushing {len(secrets)} secret(s) to Vercel "
        f"({', '.join(targets)})..."
    )

    if dry_run:
        for secret in secrets:
            click.echo(f"  would push {secret.key} -> {', '.join(targets)}")
        return

    pushed = 0
    failed = 0
    for secret in secrets:
        ok, err = _push_one(
            vercel_exe, secret.key, secret.value, targets, curdir,
        )
        if ok:
            click.secho(f"  pushed {secret.key}", fg='green')
            pushed += 1
        else:
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
        click.secho(f"Pushed {pushed} secret(s) to Vercel.", fg='green')
