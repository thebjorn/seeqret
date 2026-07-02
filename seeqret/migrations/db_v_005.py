"""Migration 005 -- Display name.

   ``users.username`` is the machine identity (``user@host``), so
   nothing in the vault identified the *person*. ``name`` carries the
   human display name: the team lead's invite sets ``onboarding.name``
   and jseeqret copies it onto the user row at approval. Nullable, so
   vaults written by older versions of either tool stay readable.

   This migration must stay byte-compatible with the JavaScript port.
"""

import sqlite3
import click
from ..run_utils import cd
from .utils import column_exists


def init_db_v_005(vault_dir):
    """Apply schema migration 005 to the vault database.

       - Add a nullable ``name`` column to the users table.
       - Add a nullable ``name`` column to the onboarding table.
    """
    click.echo(f'Initializing database version 0.0.5 in {vault_dir}')

    with cd(vault_dir):
        cn = sqlite3.connect('seeqrets.db')
        with cn:
            c = cn.cursor()

            if not column_exists(cn, 'users', 'name'):
                c.execute('''
                    alter table users add column name text;
                ''')
            if not column_exists(cn, 'onboarding', 'name'):
                c.execute('''
                    alter table onboarding add column name text;
                ''')

            c.execute('''
                insert or ignore into migrations (version)
                values (5);
            ''')
            cn.commit()
        cn.close()
