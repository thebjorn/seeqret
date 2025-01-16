# import os
from pathlib import Path
# import textwrap
import click

from . import seeqret_init
from .fileutils import is_writable
from .run_utils import current_user


@click.command()
@click.pass_context
@click.option('--email', prompt=True, help='Your email address')
@click.option('--pubkey', prompt=True, help='Your public key')
def init(ctx, email, pubkey):
    """Initialize a server vault
    """
    dirname = Path('/srv')
    vault_dir = dirname / '.seeqret'

    # we want to create dirname / seeqret

    if not dirname.exists():
        # click.echo(f'The parent of the vault: {dirname} must exist.')
        ctx.fail(f'The parent of the vault: {dirname} must exist.')
        # return

    # if not is_writable(dirname):
    #     click.echo(f'The parent of the vault: {dirname} is not writable.')
    #     if click.confirm("Do you want me to try to fix this?"):
    #         pass
    #     else:
    #         ctx.fail(f'The parent of the vault: {dirname} must be writable.')
    #     # ctx.fail(f'The parent of the vault: {dirname} must be writable.')
    #     # return

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

    curuser = current_user()
    # pkey_fname = os.path.expanduser('~/.ssh/seeqret-private.key')
    # pubkey_fname = os.path.expanduser('~/.ssh/seeqret-public.key')

    # if not os.path.exists(pkey_fname):
    #     click.secho(f"Private key {pkey_fname} does not exist", fg='red')
    #     click.echo(textwrap.dedent("""
    #         Please create a private key and public key in
    #
    #             ~/.ssh/seeqret-private.key
    #
    #         and
    #             ~/.ssh/seeqret-public.key
    #
    #         (run `seeqret keys` locally to display your keys).
    #     """))
    #     return
    # if not os.path.exists(pubkey_fname):
    #     click.secho(f"Public key {pubkey_fname} does not exist", fg='red')
    #     return

    # user_pkey = load_private_key(pkey_fname)
    # user_pubkey = load_public_key(pubkey_fname)
    #
    seeqret_init.secrets_server_init(dirname, vault_dir, curuser, email, pubkey)
    #
    #
    # seeqret_init.secrets_init(dirname, user, email, pubkey, key)
