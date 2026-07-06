"""GUI-facing facade over the seeqret core.

   This is the only module in ``seeqret.gui`` that imports from the
   core packages (``storage``, ``models``, ``run_utils``). Each
   method corresponds to one of jseeqret's IPC channels, so the two
   GUIs stay conceptually aligned.

   No chdir is needed: ``SqliteStorage.connection()`` and
   ``Secret.value`` both resolve the vault through
   ``get_seeqret_dir()`` (the ``SEEQRET`` env var), not the CWD.
"""
import os

from ..filterspec import FilterSpec
from ..models import Secret
from ..run_utils import get_seeqret_dir, is_initialized, qualified_user
from ..seeqrypt.nacl_backend import fingerprint
from ..storage.sqlite_storage import SqliteStorage
from .. import __version__


class VaultFacade:
    """In-process replacement for jseeqret's IPC surface.
    """

    def __init__(self):
        self.storage = SqliteStorage()

    # ---- vault:status ------------------------------------------------

    def vault_status(self) -> dict:
        """Vault availability + identity summary (cf. ``vault:status``).
        """
        initialized = is_initialized()
        status = dict(
            initialized=initialized,
            vault_dir=get_seeqret_dir() if 'SEEQRET' in os.environ else None,
            current_user=qualified_user(),
            version=__version__,
            owner=None,
        )
        if initialized:
            admin = self.storage.fetch_admin()
            if admin:
                status['owner'] = admin.username
        return status

    # ---- secrets:* ---------------------------------------------------

    def list_secrets(self, filterspec: str = '*:*:*') -> list[dict]:
        """Decrypted secrets matching a glob filter (cf. ``secrets:list``).
        """
        filters = FilterSpec(filterspec).to_filterdict()
        return [s.to_plaintext_dict()
                for s in self.storage.fetch_secrets(**filters)]

    def add_secret(self, app: str, env: str, key: str,
                   value: str, type: str = 'str') -> None:
        """Encrypt and store a new secret (cf. ``secrets:add``).
        """
        secret = Secret(app=app, env=env, key=key,
                        plaintext_value=value, type=type)
        self.storage.add_secret(secret)

    def update_secret_value(self, app: str, env: str, key: str,
                            value: str, type: str = 'str') -> None:
        """Change the value of an existing secret (cf. ``secrets:update``).

           The identity (app, env, key) is immutable, mirroring
           jseeqret's edit dialog.
        """
        secret = Secret(app=app, env=env, key=key,
                        plaintext_value=value, type=type)
        self.storage.update_secret(secret)

    def remove_secret(self, app: str, env: str, key: str) -> None:
        """Delete a single secret (cf. ``secrets:remove``).
        """
        self.storage.remove_secrets(app=app, env=env, key=key)

    # ---- users:* -----------------------------------------------------

    def list_users(self) -> list[dict]:
        """Users with fingerprint and owner flag (cf. ``users:list``).
        """
        admin = self.storage.fetch_admin()
        owner_name = admin.username if admin else None
        res = []
        for user in self.storage.fetch_users():
            rec = user.__json__()
            rec['fingerprint'] = fingerprint(user.pubkey.encode('utf-8'))
            rec['is_owner'] = user.username == owner_name
            res.append(rec)
        return res

    # ---- vault:introduction --------------------------------------------

    def introduction(self) -> dict | None:
        """The current user's shareable identity (cf. ``vault:introduction``).

           Returns None when the current user is not registered in
           the vault.
        """
        user = self.storage.fetch_user(qualified_user())
        if not user:
            return None
        cmd = (f'seeqret add user --username {user.username} '
               f'--email {user.email} --pubkey {user.pubkey}')
        if user.name:
            cmd += f' --name "{user.name}"'
        return dict(
            username=user.username,
            name=user.name,
            email=user.email,
            pubkey=user.pubkey,
            fingerprint=fingerprint(user.pubkey.encode('utf-8')),
            add_command=cmd,
        )
