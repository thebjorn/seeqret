import sqlite3
# import click
from seeqret.migrations.utils import current_version
from ..run_utils import cd

from . import (
    db_v_001,
    db_v_002,
)


def init_db(vault_dir, user, email):
    with cd(vault_dir):
        cn = sqlite3.connect('seeqrets.db')
        with cn:
            cur = current_version(cn)
            if cur < 1:
                db_v_001.init_db_v_001(vault_dir, user, email)
            if cur < 2:
                db_v_002.init_db_v_002(vault_dir)
        cn.close()
