import textwrap
from os import abort

import click
import os
import sys

from seeqret.migrations.initialize_database import init_db
# from seeqret.db_utils import fetch_admin
from seeqret.seeqret_add import add_user
from seeqret.seeqrypt.nacl_backend import (
    generate_private_key,
    private_key,
    public_key,
    save_public_key,
)
from seeqret.storage.sqlite_storage import SqliteStorage
from .seeqrypt.utils import generate_symetric_key

from .fileutils import is_encrypted, attrib_cmd, write_binary_file
from .run_utils import run, seeqret_dir, cd

DRIVE_TYPES = {
    0: 'Drive Unknown',
    1: 'No Root Directory',
    2: 'Drive Removable',
    3: 'Drive Fixed',
    4: 'Drive Network',
    5: 'Drive CD',
    6: 'Drive RAMdisk'
}


def _validate_vault_dir(dirname, vaultname):
    # we can't store secrets in a vcs repository!
    vcs_dirs = ['.svn', '.git', '.hg', '.bzr']
    for parent in list(dirname.parents) + [dirname]:
        for vcs in vcs_dirs:
            if parent.joinpath(vcs).exists():
                if vcs == '.git':
                    # ignore vaultname directory (add to .gitignore)
                    with open(parent.joinpath('.gitignore'), 'a') as f:
                        f.write(f'\n{vaultname}\n')
                elif vcs == '.svn':
                    # ignore vaultname directory
                    run(f"svn propset svn:ignore {vaultname} .", workdir=parent)
                elif vcs == '.hg':
                    # ignore vaultname directory (add to .hgignore)
                    with open(parent.joinpath('.hgignore'), 'a') as f:
                        f.write(f'\n{vaultname}\n')
                elif vcs == '.bzr':
                    # ignore vaultname directory (add to .bzrignore)
                    with open(parent.joinpath('.bzrignore'), 'a') as f:
                        f.write(f'\n{vaultname}\n')
                else:
                    click.echo(f'{parent} is a {vcs[1:]} repository, aborting.')
                    return False

    if sys.platform == 'win32':
        from win32 import win32file
        drive = os.path.splitdrive(os.path.abspath(dirname))[0]
        drive_type = win32file.GetDriveType(drive)
        if drive_type == 4:
            click.echo(f'{drive} is not a local drive, aborting.')
            click.echo(f'win32file.GetDriveType("{drive}")'
                       f' returned {drive_type}.')
            if not click.confirm('Do you want to continue?'):
                return False

    return True


def secrets_server_init(dirname, vault_dir, curuser, email, pubkey):
    owner = run("hostname").split('.')[0]
    print("SEQRET:SERVER_INIT")
    if not _validate_vault_dir(dirname, '.seeqret'):
        return False
    setup_vault(vault_dir, curuser, type='server')
    create_user_keys(vault_dir, owner)
    init_db(vault_dir, owner, f"{owner}@{owner}")
    with cd(os.path.join(dirname, '.seeqret')):
        add_user(pubkey, curuser, email)
    # TODO: we'll need system public/private keys so exports are from the
    #       system user...
    #       This means that each user will need to add the system user
    #       (eg. hostname) as a user in their own vault.
    # create_system_key(vault_dir)


# seeqret init
def secrets_init(dirname, user, email, pubkey=None, key=None):
    # dirname is the parent of seeqret..!
    seeqret_dir = dirname / 'seeqret'

    click.echo(textwrap.dedent(f'''
        Initializing seeqret vault for {user} in {dirname}
        by creating a new directory {seeqret_dir} and setting permissions.
    '''))

    if not _validate_vault_dir(dirname, 'seeqret'):
        return False
    setup_vault(seeqret_dir, user, type='client')
    create_user_keys(seeqret_dir, user, pubkey, key)
    init_db(seeqret_dir, user, email)


def create_system_key(vault_dir):
    with cd(vault_dir):
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


def create_user_keys(vault_dir, user, pubkey=None, key=None):
    with cd(vault_dir):
        click.echo('Checking for existing user keys')
        if os.path.exists('public.key') and os.path.exists('private.key'):
            click.secho(f'User keys already exist for {user}', fg='green')
        else:
            click.echo(f'Creating keys for {user}')
            if key:
                # FIXME: use the nacl_backend functions
                #        for reading/writing keys?
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

        create_system_key(vault_dir)

        if os.environ.get('TESTING', "") == "TRUE":
            os.environ["SEEQRET"] = os.path.abspath(vault_dir)
        else:
            if sys.platform == 'win32':
                run(f'setx SEEQRET {os.path.abspath(vault_dir)}')

    if sys.platform == 'win32':
        click.echo("I've set the SEEQRET environment variable to the vault "
                   "directory")
        click.echo("Please close this window and open a new one to continue.")
        click.echo('or run\n\n')
        click.echo(f'    set "SEQRET={os.path.abspath(vault_dir)}"')
        click.echo('\n\nin the current window to continue here.')


# seeqret upgrade
def upgrade_db():
    with seeqret_dir():
        storage = SqliteStorage()
        admin = storage.fetch_admin()
        if not admin:
            return False
        init_db(os.environ['SEEQRET'], admin.username, admin.email)


def setup_vault(vault_dir, user, type='client'):

    if os.name == 'nt':
        if not vault_dir.exists():
            click.echo(f'creating {vault_dir}.')
            vault_dir.mkdir(0o770)

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
        # linux... (server vault or CI)
        if type == 'client':
            vault_dir.mkdir(0o770)
            return

        click.echo(textwrap.dedent(f"""\
            - I will now create a group called 'seeqret' and add the current user to it.
            - I will also set the permissions on the {vault_dir.parent} to be
              owned by group 'seeqret' and set the groupid and sticky bits.
            - I will then set the permissions on the vault_dir to 770.
        """))

        if not click.confirm("Do you want to continue?"):
            abort()
        if not vault_dir.exists():
            click.secho('adding group seeqret...', fg='blue')
            run("sudo getent group seeqret || sudo groupadd seeqret")
            if not run("sudo getent group seeqret"):
                click.echo("Could not create group seeqret")
                abort()

            click.secho(f'adding user {user} to group seeqret...', fg='blue')
            run(f"sudo usermod -aG seeqret {user}")
            if 'seeqret' not in run(f"groups {user}"):
                click.echo("Could not add user to group seeqret")
                abort()

            click.secho(f'changing group ownership of {vault_dir.parent} to seeqret...', fg='blue')
            run(f"sudo chgrp seeqret {vault_dir.parent}")

            click.secho(f'setting permissions on {vault_dir.parent}...', fg='blue')
            run(f"sudo chmod g+s {vault_dir.parent}")
            run(f"sudo chmod g+w {vault_dir.parent}")
            try:
                vault_dir.mkdir(0o770)
            except PermissionError:
                click.echo("You must login again, and reissue the command to continue.")
                abort()
        run(f"sudo chmod g+w {vault_dir}")
