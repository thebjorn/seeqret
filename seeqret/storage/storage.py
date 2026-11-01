from ..models import Secret, User


class SecretNotFound(KeyError, IndexError):
    """No secret matches the requested key/app/env.

    Subclasses IndexError as well as KeyError, so callers that caught
    the IndexError raised by earlier versions keep working.
    """
    def __init__(self, key, app='*', env='*', location=None):
        self.key = key
        self.app = app
        self.env = env
        self.location = location
        super().__init__(key)

    def __str__(self):
        where = f' in vault {self.location}' if self.location else ''
        return (
            f'No secret {self.app}:{self.env}:{self.key}{where}.\n'
            f'See where {self.key!r} exists with: '
            f'seeqret list "*:*:{self.key}"'
        )


class AmbiguousSecret(LookupError):
    """More than one secret matches the requested key/app/env.
    """
    def __init__(self, key, app, env, matches):
        self.key = key
        self.app = app
        self.env = env
        # app:env:key strings only -- never keep Secret objects here, their
        # repr decrypts the value and this exception may end up in a log.
        self.matches = sorted(f'{s.app}:{s.env}:{s.key}' for s in matches)
        super().__init__(key)

    def __str__(self):
        listing = '\n'.join(f'    {m}' for m in self.matches)
        return (
            f'{len(self.matches)} secrets match '
            f'{self.app}:{self.env}:{self.key}:\n{listing}\n'
            f'Name the app and env, e.g. seeqret.get({self.matches[0]!r}).'
        )


class Storage:
    """Base class for storage backends.
    """
    def __init__(self, name, version=None):
        self.name = name
        self.version = version

    def add_user(self, user: User):
        raise NotImplementedError

    def remove_user(self, username: str):
        raise NotImplementedError   # pragma: no cover

    def fetch_user(self, username: str):
        raise NotImplementedError   # pragma: no cover

    def fetch_users(self, **filters):
        raise NotImplementedError   # pragma: no cover

    def fetch_admin(self):
        raise NotImplementedError   # pragma: no cover

    def add_secret(self, app, env, key, value, type='str'):
        raise NotImplementedError   # pragma: no cover

    def add_secret_obj(self, secret: Secret):
        self.add_secret(
            secret.app,
            secret.env,
            secret.key,
            secret.value,
            secret.type,
        )

    def fetch_secrets(self, **filters):
        raise NotImplementedError   # pragma: no cover

    def storage_location(self) -> str | None:
        """Human-readable location of the vault, used in error messages.
        """
        return None

    def fast_get_secret(self, key, app='*', env='*'):
        secrets = self.fetch_secrets(key=key, app=app, env=env)
        if not secrets:
            raise SecretNotFound(key, app, env, self.storage_location())
        if len(secrets) > 1:
            raise AmbiguousSecret(key, app, env, secrets)
        return secrets[0]

    def remove_secrets(self, **filters):
        raise NotImplementedError
