import sqlite3
import textwrap
from os import abort

import click
import os
import sys

from seeqret.migrations.initialize_database import init_db
from seeqret.seeqret_add import fetch_admin
from seeqret.seeqrypt.nacl_backend import (
    generate_private_key,
    private_key,
    public_key,
    save_public_key,
)
from seeqret.seeqrypt.utils import generate_symetric_key

from seeqret.utils import cd, is_encrypted, run, attrib_cmd, write_binary_file


def _validate_vault_dir(dirname):
    # we can't store secrets in a vcs repository!
    vcs_dirs = ['.svn', '.git', '.hg', '.bzr']
    for parent in list(dirname.parents) + [dirname]:
        for vcs in vcs_dirs:
            if parent.joinpath(vcs).exists():
                click.echo(f'{parent} is a {vcs[1:]} repository, aborting.')
                abort()

    if sys.platform == 'win32':
        import win32file
        drive = os.path.splitdrive(os.path.abspath(dirname))[0]
        if not win32file.GetDriveType(drive) == 4:
            click.echo(f'{drive} is not a local drive, aborting.')
            abort()


def secrets_init(dirname, user, email, pubkey=None, key=None):
    # dirname is the parent of seeqret..!
    seeqret_dir = dirname / 'seeqret'

    click.echo(textwrap.dedent(f'''
        Initializing seeqret vault for {user} in {dirname}
        by creating a new directory {seeqret_dir} and setting permissions.
    '''))

    _validate_vault_dir(dirname)
    setup_vault(seeqret_dir)
    create_user_keys(seeqret_dir, user, pubkey, key)
    init_db(seeqret_dir, user, email)


def create_user_keys(vault_dir, user, pubkey=None, key=None):
    with cd(vault_dir):
        click.echo('Checking for existing user keys')
        if os.path.exists('public.key') and os.path.exists('private.key'):
            click.secho(f'User keys already exist for {user}', fg='green')
        else:
            click.echo(f'Creating keys for {user}')
            if key:
                write_binary_file('private.key', key.encode('ascii'))
                pkey = private_key(key)
            else:
                pkey = generate_private_key('private.key')
            if pubkey:
                write_binary_file('public.key', pubkey.encode('ascii'))
                pubkey = public_key(pubkey)
            else:
                pubkey = save_public_key('public.key', pkey)
            click.secho(f'Keys created for {user}', fg='green')
            click.secho(f'Please publish your public key: {pubkey}', fg='blue')

        if os.path.exists('seeqret.key'):
            click.secho('seeqret.key already exists', fg='green')
        else:
            click.echo('Creating seeqret.key')
            generate_symetric_key('seeqret.key')
            if os.path.exists('seeqret.key'):
                click.secho('seeqret.key created', fg='green')
            else:
                click.secho('seeqret.key creation failed', fg='red')
                abort()
        run(f'setx SEEQRET {os.path.abspath(vault_dir)}')
    click.echo("I've set the SEEQRET environment variable to the vault "
               "directory")
    click.echo("Please close this window and open a new one to continue.")
    click.echo('or run\n\n')
    click.echo(f'    set "SEQRET={os.path.abspath(vault_dir)}"')
    click.echo('\n\nin the current window to continue here.')


def upgrade_db():
    with cd(os.environ['SEEQRET']):
        cn = sqlite3.connect('seeqrets.db')
        with cn:
            admin = fetch_admin(cn)
        init_db(os.environ['SEEQRET'], admin['username'], admin['email'])


def setup_vault(vault_dir):
    if not vault_dir.exists():
        click.echo(f'creating {vault_dir}.')
        vault_dir.mkdir(0o770)

    if os.name == 'nt':
        with cd(vault_dir.parent):
            seeqret_dir = str(vault_dir)
            if len(run(f"icacls {seeqret_dir}").splitlines()) >= 4:
                click.echo(f"Tightening permissions on {vault_dir}")
                click.echo("Granting (F)ull rights to current user only")
                userdomain = os.environ['USERDOMAIN']
                username = os.environ['USERNAME']
                current_user = f'{userdomain}\\{username}'
                run(f"icacls {seeqret_dir} /grant {current_user}:(F)")
                click.echo("Removing all inherited permissions")
                run(f"icacls {seeqret_dir} /inheritance:r")
                click.echo("Verifying permissions..")
                if len(run("icacls " + seeqret_dir).splitlines()) >= 4:
                    click.echo("Could not change permissions on vault_dir")
            click.echo("vault_dir permissions are ok")

            click.echo("Checking if vault_dir is indexed by windows search")
            if 'I' not in attrib_cmd(seeqret_dir):
                click.echo(f"Removing {vault_dir} from windows indexing.")
                attrib_cmd(seeqret_dir, '+I')
            else:
                click.secho(f"{vault_dir} is not indexed", fg='green')

            if not is_encrypted("seeqret"):
                click.echo(f"encrypting {vault_dir}")
                run("cipher /e seeqret")
                click.echo("Checking if encryption worked..")
                if not is_encrypted("seeqret"):
                    click.echo(
                        "cipher /e seeqret (this is very bad, aborting...)"
                    )
                    # this is very, very bad..
                    abort()
                else:
                    click.echo("vault is encrypted")
            else:
                click.echo("vault is encrypted")
    else:
        click.echo("Not on Windows, skipping permissions setup.")
