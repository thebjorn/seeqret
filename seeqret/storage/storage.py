

class Storage:
    """Base class for storage backends.
    """
    def __init__(self, name, version=None):
        self.name = name
        self.version = version

    def fetch_users(self, **filters):
        raise NotImplementedError   # pragma: no cover

    def fetch_admin(self):
        raise NotImplementedError   # pragma: no cover

    def fetch_secrets(self, **filters):
        raise NotImplementedError   # pragma: no cover
