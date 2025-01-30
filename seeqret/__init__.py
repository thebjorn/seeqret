# import sqlite3

# from seeqret.seeqrypt.aes_fernet import decrypt_string
# from seeqret.seeqrypt.utils import load_symetric_key
# from seeqret.run_utils import seeqret_dir
from seeqret.storage.get_secret import get_secret

__version__ = '0.1.7'


def get(key, app='*', env='*'):
    """Get a value from the configuration.

    Args:
        key: The key to get.
        app: The application to get the key from.
        env: The environment to get the key from.

    Returns:
        The value of the key.
    """
    return get_secret(key, app, env)
    # with seeqret_dir():
    #     cipher = load_symetric_key('seeqret.key')
    #     # open the database in read-only mode
    #     cn = sqlite3.connect('file:seeqrets.db?mode=ro', uri=True)
    #     cursor = cn.cursor()
    #     cursor.execute(
    #         "select value from secrets where app = ? and env = ? and key = ?",
    #         (app, env, key)
    #     )
    #     result = cursor.fetchone()
    #     cursor.close()
    #     cn.close()
    #     return decrypt_string(cipher, result[0]) if result else None
