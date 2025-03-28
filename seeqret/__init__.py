from seeqret.storage.get_secret import get_secret

__version__ = '0.2.0'


def get(key, app='*', env='*'):
    """Get a value from the configuration.

    Important: to keep your secrets out of tracebacks etc., you should call
    this function at the last possible moment. I.e., instead of having a
    settings file with:

        DB_PASSWORD = seeqret.get("db_password")  # BAD!

    do:

        cn = mydb.connect(..., password=seeqret.get("db_password"))  # GOOD!

    Args:
        key: The key to get.
        app: The application to get the key from.
        env: The environment to get the key from.

    Returns:
        The value of the key.
    """
    return get_secret(key, app, env)
