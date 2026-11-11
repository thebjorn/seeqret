from seeqret.storage.get_secret import get_secret
from seeqret.storage.storage import AmbiguousSecret, SecretNotFound

__all__ = ['get', 'AmbiguousSecret', 'SecretNotFound']

__version__ = '2.0.5'


def get(key, app='*', env='*'):
    """Get a value from the configuration.

    Important: to keep your secrets out of tracebacks etc., you should call
    this function at the last possible moment. I.e., instead of having a
    settings file with:

        DB_PASSWORD = seeqret.get("db_password")  # BAD!

    do:

        cn = mydb.connect(..., password=seeqret.get("db_password"))  # GOOD!

    The secret can be named the same way as on the command line:

        seeqret.get('yerbu:prod:CRON_SECRET')
        seeqret.get('CRON_SECRET', app='yerbu', env='prod')  # same thing

    Args:
        key: The key name, or an ``app:env:key`` reference (empty parts
            mean ``*``).
        app: The application to get the key from (only with a bare key).
        env: The environment to get the key from (only with a bare key).

    Returns:
        The value of the key.

    Raises:
        SecretNotFound: no secret matches key/app/env. It is a KeyError
            (and an IndexError, for backward compatibility).
        AmbiguousSecret: more than one secret matches (e.g. ``::KEY`` when
            KEY exists in both prod and dev). It is a LookupError.
        ValueError: ``key`` is a malformed reference, or an ``app:env:key``
            reference combined with explicit app/env.
    """
    return get_secret(key, app, env).value
