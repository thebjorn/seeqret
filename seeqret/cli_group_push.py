"""Click command group for ``seeqret push ...``.

   Push secrets from the local vault out to external systems
   (currently: Vercel projects via the ``vercel`` CLI).
"""

import json
import os
import shutil
import subprocess

import click

from .filterspec import FilterSpec
from .run_utils import seeqret_dir
from .storage.sqlite_storage import SqliteStorage


VERCEL_TARGETS = ('production', 'preview', 'development')


def _repo_json_covers(curdir) -> bool:
    """Check for a monorepo-style Vercel link covering ``curdir``.

       Newer Vercel CLIs (``vercel link`` inside a git repo) write a
       single ``.vercel/repo.json`` at the repo root instead of a
       per-directory ``.vercel/project.json``. The vercel CLI resolves
       the project from the subdirectory it is invoked in, so pushing
       works as long as ``curdir`` is one of the linked project
       directories listed in repo.json.
    """
    curdir = os.path.abspath(curdir)
    d = curdir
    while True:
        repo_file = os.path.join(d, '.vercel', 'repo.json')
        if os.path.exists(repo_file):
            try:
                with open(repo_file) as f:
                    repo = json.load(f)
            except (OSError, ValueError):
                return False
            reldir = os.path.relpath(curdir, d).replace(os.sep, '/')
            return any(
                p.get('directory') == reldir
                for p in repo.get('projects', [])
            )
        parent = os.path.dirname(d)
        if parent == d:
            return False
        d = parent


def _check_vercel_linked(ctx, curdir) -> str:
    """Verify ``vercel`` is on PATH and the current dir is a linked project.

       Accepts either a per-directory link (``.vercel/project.json`` in
       ``curdir``) or a monorepo link (``.vercel/repo.json`` in an
       ancestor directory listing ``curdir`` as a project directory).

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
    if not os.path.exists(project_file) and not _repo_json_covers(curdir):
        ctx.fail(
            f"No linked Vercel project found in {curdir} "
            "(no .vercel/project.json here, and no ancestor "
            ".vercel/repo.json lists this directory as a project). "
            "Run `vercel link` from this directory first."
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
@click.option('--target', required=True,
              help='Comma-separated Vercel environments to push to '
                   '(production, preview, development). Required, so a '
                   'push never hits an environment you did not name.')
@click.option('--dry-run', is_flag=True,
              help='Show what would be pushed without making changes.')
def vercel(ctx, filterspec, filter_, target, dry_run):
    """Push secrets matching FILTER to the linked Vercel project.

    The Vercel CLI must be installed and the current directory must be
    a linked project (run `vercel link` first). Existing variables with
    the same name on the chosen targets are overwritten.

    \b
    Examples:
        seeqret push vercel myapp:prod:* --target production
        seeqret push vercel --filter myapp:prod:DB_* --target production
        seeqret push vercel myapp:prod:* --target production,preview
        seeqret push vercel myapp:prod:* --target production --dry-run
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
