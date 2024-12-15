import sqlite3
import textwrap
from os import abort

import click
import os

from seeqret.migrations.initialize_database import init_db
from seeqret.seeqret_add import fetch_admin
from seeqret.seeqrypt.nacl_backend import generate_private_key, save_public_key
from seeqret.seeqrypt.utils import generate_symetric_key

from seeqret.utils import cd, is_encrypted, run, attrib_cmd


def secrets_init(dirname, user, email, ctx):
    # dirname is the parent of seeqret..!
    seeqret_dir = dirname / 'seeqret'

    click.echo(textwrap.dedent(f'''
        Initializing seeqret vault for {user} in {dirname}
        by creating a new directory {seeqret_dir} and setting permissions.
    '''))

    setup_vault(seeqret_dir)
    create_user_keys(seeqret_dir, user, ctx)
    init_db(seeqret_dir, user, email)


def create_user_keys(vault_dir, user, ctx):
    with cd(vault_dir):
        click.echo('Checking for existing user keys')
        if os.path.exists('public.key') and os.path.exists('private.key'):
            click.secho(f'User keys already exist for {user}', fg='green')
        else:
            click.echo(f'Creating keys for {user}')
            pkey = generate_private_key('private.key')
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
