from .sqlite_storage import SqliteStorage


def get_secret(key, app='*', env='*'):
    storage = SqliteStorage()
    return storage.fast_get_secret(key, app, env)
