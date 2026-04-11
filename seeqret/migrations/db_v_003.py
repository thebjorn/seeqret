"""Migration 003 -- Slack exchange support.

Mirrors jseeqret's v3 schema so the two tools share a database:

  - users gains slack_handle, slack_key_fingerprint, slack_verified_at
  - new kv table for Fernet-encrypted Slack tokens and channel config

See documentation/slack-exchange/PLAN.md for the rationale. This
migration must stay byte-compatible with the JavaScript port.
"""

import sqlite3
import click
from ..run_utils import cd
from .utils import column_exists, table_exists


def init_db_v_003(vault_dir):
    """Migration 003

       - Add columns slack_handle, slack_key_fingerprint,
         slack_verified_at to the users table
       - Create a new kv table for Fernet-encrypted configuration
         (Slack user token, channel id, last_seen_ts, etc.)

    """
    click.echo(f'Initializing database version 0.0.3 in {vault_dir}')

    with cd(vault_dir):
        cn = sqlite3.connect('seeqrets.db')
        with cn:
            c = cn.cursor()

            if not column_exists(cn, 'users', 'slack_handle'):
                c.execute('''
                    alter table users add column slack_handle text;
                ''')
            if not column_exists(cn, 'users', 'slack_key_fingerprint'):
                c.execute('''
                    alter table users
                    add column slack_key_fingerprint text;
                ''')
            if not column_exists(cn, 'users', 'slack_verified_at'):
                c.execute('''
                    alter table users
                    add column slack_verified_at integer;
                ''')

            if not table_exists(cn, 'kv'):
                c.execute('''
                    create table if not exists kv (
                        key             text primary key,
                        encrypted_value blob not null,
                        updated_at      integer not null
                    );
                ''')

            c.execute('''
                insert or ignore into migrations (version)
                values (3);
            ''')
            cn.commit()
        cn.close()
