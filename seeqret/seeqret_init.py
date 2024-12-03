import click
import os
import pathlib

from seeqret.utils import cd


def secrets_init(dirname):
    click.echo('Initializing seeqret for a new user')

    # verify that the directory exists
    if not os.path.exists(dirname):
        click.echo(f'Directory {dirname} does not exist, creating it.')
        setup_vault(dirname)
    
    # verify that the directory is secure
    if not os.access(dirname, os.W_OK):
        click.echo(f'Directory {dirname} is not writable')
        return

    # Create the .seeqret file
    open(os.path.join(dirname, '.seeqret'), 'w').close()



def setup_vault(dirname):
    vault_dir = dirname / 'seeqret'
    # sourcery skip: extract-method, use-fstring-for-concatenation
    if not vault_dir.exists():
        click.echo(f'creating {vault_dir}.')
        vault_dir.mkdir(0o770)

    if os.name == 'nt':
        with cd(vault_dir.parent):
            if len(run(f"icacls {vault_dir}").splitlines()) >= 4:
                click.echo(f"Tightening permissions on {vault_dir}")
                ctx.log("Granting (F)ull rights to current user only")
                run(f"icacls {vault_dir} /grant {os.environ['USERDOMAIN']}\\{os.environ['USERNAME']}:(F)")
                click.echo("Removing all inherited permissions")
                run(f"icacls {vault_dir} /inheritance:r")
                if len(run("icacls " + vault_dir).splitlines()) >= 4:
                    click.echo("Could not change permissions on vault_dir")
            click.echo("vault_dir permissions are ok")

            if 'I' not in attrib_cmd(vault_dir):
                click.echo(f"Removing {vault_dir} from windows indexing.")
                attrib_cmd(vault_dir, '+I')

            if run(f"cipher /c {vault_dir} | grep vault_dir").split()[0] == 'U':
                click.echo(f"encrypting {vault_dir}")
                run(f"cipher /e {vault_dir}")
                if run(f"cipher /c {vault_dir} | grep vault_dir").split()[0] == 'U':
                    click.echo(f"Couldn't encrypt with cipher /c {vault_dir}")
            else:
                click.echo(f"{vault_dir} is encrypted")

    # TODO: run dkpw init? (might clobber existing installation, when moving from svn to git).
    ctx.vault_dir = vault_dir
    click.echo("""
        You need to run dkpw init to create the dkpasswords file.
        Then `run dkpw export ""` on an existing installation, and
        copy the output into a terminal in this installation.
    """)