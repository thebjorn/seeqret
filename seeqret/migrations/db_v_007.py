"""Migration 007 -- SSH remote targets.

   ``remotes`` maps a short alias (e.g. ``fischer``) to an ssh
   identity (``username@hostname``) plus the command templates used to
   push and verify secrets on that host. The templates live in the
   vault -- not in the code -- so seeqret has no intrinsic knowledge of
   private server-side tools: ``{key}`` and ``{value}`` placeholders
   are substituted (shell-quoted) at run time.

   This migration must stay byte-compatible with the JavaScript port
   (jseeqret needs a mirroring migration 007).
"""

import sqlite3
import click
from ..run_utils import cd
from .utils import table_exists


def init_db_v_007(vault_dir):
    """Apply schema migration 007 to the vault database.

       - Create the ``remotes`` table (alias -> ssh host + push/verify
         command templates).
    """
    click.echo(f'Initializing database version 0.0.7 in {vault_dir}')

    with cd(vault_dir):
        cn = sqlite3.connect('seeqrets.db')
        with cn:
            c = cn.cursor()

            if not table_exists(cn, 'remotes'):
                c.execute('''
                    create table if not exists remotes (
                        alias      text primary key,
                        username   text not null,
                        hostname   text not null,
                        set_cmd    text not null,
                        get_cmd    text,
                        created_at integer not null,
                        updated_at integer not null
                    );
                ''')

            c.execute('''
                insert or ignore into migrations (version)
                values (7);
            ''')
            cn.commit()
        cn.close()
