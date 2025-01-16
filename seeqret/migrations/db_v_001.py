import sqlite3
import click
from ..run_utils import cd


def init_db_v_001(vault_dir, user, email):
    """Migration 001

       - Add tables: migrations, users, secrets
       - indexes: idx_users_username, idx_secrets_key
       - insert owner user as id 1

    """
    click.echo(f'Initializing database version 0.0.1 in {vault_dir}')
    # create a database in the vault_dir
    with cd(vault_dir):
        cn = sqlite3.connect('seeqrets.db')
        with cn:
            c = cn.cursor()
            c.execute('''
                create table if not exists migrations (
                    id integer primary key,
                    version integer not null,
                    applied_at datetime not null default(current_timestamp)
                );
            ''')
            c.execute('''
                insert or ignore into migrations (version)
                values (1);
            ''')
            c.execute('''
                create table if not exists users (
                    id integer primary key,
                    username text not null,
                    email text not null,
                    pubkey text not null
                );
            ''')
            c.execute('''
                create unique index if not exists
                    idx_users_username
                on users (username);
            ''')
            c.execute('''
                create table if not exists secrets (
                    id integer primary key,
                    app text not null,
                    env text not null,
                    key text not null,
                    value text not null,

                    unique(app, env, key)
                );
            ''')
            c.execute('''
                create unique index if not exists
                    idx_secrets_key
                on secrets (app, env, key);
            ''')
            cn.commit()
        with cn:
            c = cn.cursor()
            c.execute('''
                insert or ignore into users (username, email, pubkey)
                values (?, ?, ?);
            ''', (user, email, open('public.key').read()))
            cn.commit()
        cn.close()
