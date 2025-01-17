from ..models import Secret, User


class Storage:
    """Base class for storage backends.
    """
    def __init__(self, name, version=None):
        self.name = name
        self.version = version

    def add_user(self, user: User):
        raise NotImplementedError

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

    def fast_get_secret(self, key, app='*', env='*'):
        return self.fetch_secrets(key=key, app=app, env=env)[0]

    def remove_secrets(self, **filters):
        raise NotImplementedError
