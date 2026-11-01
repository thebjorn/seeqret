from .sqlite_storage import SqliteStorage


def parse_secret_ref(key, app='*', env='*'):
    """Split an ``app:env:key`` reference into (key, app, env).

    A bare key is returned unchanged with the given app/env. Empty parts
    of a filter string mean ``*``, as in the CLI (``::KEY`` is ``*:*:KEY``).

    Raises:
        ValueError: the reference is malformed, or it is a filter string
            and app/env were also passed explicitly.
    """
    if ':' not in key:
        return key, app, env

    parts = key.split(':')
    if len(parts) != 3 or not parts[2]:
        raise ValueError(
            f'Invalid secret reference {key!r}: expected KEY or APP:ENV:KEY, '
            f"e.g. 'yerbu:prod:CRON_SECRET'."
        )
    if app != '*' or env != '*':
        raise ValueError(
            f'{key!r} already names app and env; do not also pass '
            f'app={app!r}/env={env!r}.'
        )

    ref_app, ref_env, ref_key = parts
    return ref_key, ref_app or '*', ref_env or '*'


def get_secret(key, app='*', env='*'):
    key, app, env = parse_secret_ref(key, app, env)
    storage = SqliteStorage()
    return storage.fast_get_secret(key, app, env)
