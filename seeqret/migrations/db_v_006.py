"""Migration 006 -- Secret modification timestamp.

   ``updated_at`` (unix seconds, nullable) records when a secret's
   value last changed.  It rides along in exports so an import can tell
   whose copy of a diverged secret is newer -- advisory input to
   jseeqret's merge flow, never an automatic winner-picker (clocks
   skew, and timestamps alone cannot prove that both sides changed).
   Nullable, so vaults and exports written by older versions of either
   tool stay readable.

   This migration must stay byte-compatible with the JavaScript port.
"""

import sqlite3
import click
from ..run_utils import cd
from .utils import column_exists


def init_db_v_006(vault_dir):
    """Apply schema migration 006 to the vault database.

       - Add a nullable ``updated_at`` column (unix seconds) to the
         secrets table.
    """
    click.echo(f'Initializing database version 0.0.6 in {vault_dir}')

    with cd(vault_dir):
        cn = sqlite3.connect('seeqrets.db')
        with cn:
            c = cn.cursor()

            if not column_exists(cn, 'secrets', 'updated_at'):
                c.execute('''
                    alter table secrets add column updated_at integer;
                ''')

            c.execute('''
                insert or ignore into migrations (version)
                values (6);
            ''')
            cn.commit()
        cn.close()
