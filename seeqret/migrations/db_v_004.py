"""Migration 004 -- Onboarding state machine.

   Mirrors jseeqret's v4 schema so the two tools can share a vault:
   one ``onboarding`` row per invitee, keyed by email, capturing the
   introduction fingerprint and pubkey locally so approval survives
   Slack's 24h retention.

   Python does not (yet) drive the Slack onboarding flow -- this
   migration only keeps the schema ladder identical to the JavaScript
   port. Version numbers are shared between the tools, so a vault at
   version N must contain the same tables regardless of which tool
   created it. This migration must stay byte-compatible with jseeqret.
"""

import sqlite3
import click
from ..run_utils import cd
from .utils import table_exists


def init_db_v_004(vault_dir):
    """Apply schema migration 004 to the vault database.

       - Create the ``onboarding`` table (invite/introduce/approve
         state machine used by jseeqret's Slack onboarding).
    """
    click.echo(f'Initializing database version 0.0.4 in {vault_dir}')

    with cd(vault_dir):
        cn = sqlite3.connect('seeqrets.db')
        with cn:
            c = cn.cursor()

            if not table_exists(cn, 'onboarding'):
                c.execute('''
                    create table if not exists onboarding (
                        email            text primary key,
                        username         text,
                        slack_handle     text,
                        slack_user_id    text,
                        project_filter   text,
                        fingerprint      text,
                        pubkey           text,
                        state            text not null,
                        created_at       integer not null,
                        updated_at       integer not null
                    );
                ''')

            c.execute('''
                insert or ignore into migrations (version)
                values (4);
            ''')
            cn.commit()
        cn.close()
