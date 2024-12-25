import sqlite3
import click
from .. import cd
from .utils import (
    column_exists,
)


def init_db_v_002(vault_dir):
    """Migration 002

       - Add columns: type, updated to secrets table

    """
    click.echo(f'Initializing database version 0.0.2 in {vault_dir}')

    with cd(vault_dir):
        cn = sqlite3.connect('seeqrets.db')
        with cn:
            c = cn.cursor()
            if not column_exists(cn, 'secrets', 'type'):
                c.execute('''
                    alter table secrets
                    add column type text not null default('str');
                ''')
            if not column_exists(cn, 'secrets', 'updated'):
                c.execute('''
                    alter table secrets add column updated bool default(false);
                ''')
            c.execute('''
                insert or ignore into migrations (version)
                values (2);
            ''')
            cn.commit()
        cn.close()
