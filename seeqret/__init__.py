import os
import sqlite3

from seeqret.seeqrypt.aes_fernet import decrypt_string
from seeqret.seeqrypt.utils import load_symetric_key
from seeqret.run_utils import cd


def get(key, app='*', env='*'):
    """Get a value from the configuration.

    Args:
        key: The key to get.
        app: The application to get the key from.
        env: The environment to get the key from.

    Returns:
        The value of the key.
    """
    with cd(os.environ['SEEQRET']):
        cipher = load_symetric_key('seeqret.key')
        # open the database in read-only mode
        cn = sqlite3.connect('file:seeqrets.db?mode=ro', uri=True)
        cursor = cn.cursor()
        cursor.execute(
            "select value from secrets where app = ? and env = ? and key = ?",
            (app, env, key)
        )
        result = cursor.fetchone()
        cursor.close()
        cn.close()
        return decrypt_string(cipher, result[0]) if result else None
