"""Click command group for ``seeqret verify ...``.

   Verify that secrets in the local vault match what external systems
   (currently: Vercel projects via the ``vercel`` CLI) actually have.
"""

import os
import shutil
import subprocess
import tempfile

import click

from .cli_group_push import (
    TARGET_ALIASES, VERCEL_TARGETS, _check_vercel_linked,
)
from .cli_remote_ssh import VerifyGroup, _fetch_filtered_secrets


def _normalize_target(ctx, param, value):
    """Click callback: expand aliases and validate the target name."""
    value = TARGET_ALIASES.get(value, value)
    if value not in VERCEL_TARGETS:
        raise click.BadParameter(
            f"Unknown Vercel target: {value}. "
            f"Valid choices: {', '.join(VERCEL_TARGETS)}."
        )
    return value


def _unescape(s: str) -> str:
    """Undo backslash escapes in a double-quoted env value."""
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            nxt = s[i + 1]
            out.append({'n': '\n', 'r': '\r', 't': '\t'}.get(nxt, nxt))
            i += 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def _parse_env_file(fname: str) -> dict[str, str]:
    """Parse a ``vercel env pull`` output file into a dict.

       The file is .env formatted: ``KEY="value"`` lines with
       double-quoted, backslash-escaped values, plus comments.
    """
    env = {}
    with open(fname, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            key, _, value = line.partition('=')
            if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                value = _unescape(value[1:-1])
            env[key.strip()] = value
    return env


def _pull_env(ctx, vercel_exe: str, target: str,
              cwd: str) -> dict[str, str]:
    """Run ``vercel env pull`` into a temp file and parse it.

       The temp file (and its private temp directory) is always
       removed, so pulled secrets never linger on disk.
    """
    tmpdir = tempfile.mkdtemp(prefix='seeqret-verify-')
    tmpfile = os.path.join(tmpdir, 'vercel-env')
    try:
        pull = subprocess.run(
            [vercel_exe, 'env', 'pull',
             '--environment', target, '--yes', tmpfile],
            capture_output=True, text=True, cwd=cwd,
        )
        if pull.returncode != 0:
            err = (pull.stderr or pull.stdout).strip()
            ctx.fail(f"vercel env pull failed: {err}")
        return _parse_env_file(tmpfile)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@click.group('verify', cls=VerifyGroup)
def verify():
    """Verify that vault secrets match external systems.

    Besides the built-in targets below, any ssh remote registered
    with `seeqret remote add <alias> ... --get ...` is available as
    `seeqret verify <alias>`.
    """
    pass


@verify.command('vercel')
@click.pass_context
@click.argument('filterspec', default='')
@click.option('-f', '--filter', 'filter_', default='', show_default=False,
              help='filterspec (see '
                   'https://thebjorn.github.io/seeqret/filter-strings/)')
@click.option('--target', default='development', show_default=True,
              callback=_normalize_target,
              help='Vercel environment to verify against '
                   '(production, preview, development; prod and dev '
                   'are accepted as aliases).')
def vercel(ctx, filterspec, filter_, target):
    """Verify secrets matching FILTER against the linked Vercel project.

    Pulls the current values from Vercel with `vercel env pull` into a
    temp file, compares them to the vault values, then removes the temp
    file. Only key names and ok/MISSING/MISMATCH/SENSITIVE are printed
    -- never the values themselves.

    Vercel never returns the value of *sensitive* variables (`env pull`
    writes them as empty strings), so a secret that pulls as empty while
    the vault value is non-empty is reported as SENSITIVE (unverifiable)
    rather than a MISMATCH, and does not count as a failure.

    \b
    Examples:
        seeqret verify vercel myapp:prod:* --target production
        seeqret verify vercel --filter myapp:prod:DB_* --target prod
        seeqret verify vercel myapp:dev:*
    """
    curdir = ctx.obj.get('curdir') if ctx.obj else os.getcwd()
    curdir = curdir or os.getcwd()

    vercel_exe = _check_vercel_linked(ctx, curdir)

    secrets = _fetch_filtered_secrets(ctx, filterspec, filter_)

    click.echo(
        f"Verifying {len(secrets)} secret(s) against Vercel ({target})..."
    )
    env = _pull_env(ctx, vercel_exe, target, curdir)

    ok = 0
    failed = 0
    sensitive = 0
    for secret in secrets:
        pulled = env.get(secret.key)
        if pulled is None:
            click.secho(f"  MISSING  {secret.key}", fg='red')
            failed += 1
        elif pulled == secret.value:
            click.secho(f"  ok       {secret.key}", fg='green')
            ok += 1
        elif pulled == '':
            # Sensitive variables always pull as empty strings, so an
            # empty pull against a non-empty vault value is unverifiable
            # rather than a mismatch (empty vault values compare equal
            # above and never reach this branch).
            click.secho(
                f"  SENSITIVE {secret.key} (unverifiable)", fg='yellow'
            )
            sensitive += 1
        else:
            click.secho(f"  MISMATCH {secret.key}", fg='red')
            failed += 1

    click.echo()
    if sensitive:
        click.secho(
            f"{sensitive} sensitive secret(s) could not be verified "
            "(Vercel does not return sensitive values).",
            fg='yellow',
        )
    if failed:
        click.secho(
            f"Verified {ok}, failed {failed}.",
            fg='yellow' if ok else 'red',
        )
        ctx.exit(1)
    else:
        click.secho(
            f"Verified {ok} secret(s) against Vercel ({target}).",
            fg='green',
        )
