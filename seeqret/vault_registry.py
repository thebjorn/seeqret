"""Multi-vault registry (mirrors jseeqret's vault-registry.js).

   The registry is a flat JSON object at ``~/.seeqret/vaults.json``
   mapping vault name -> absolute path, with the reserved top-level
   key ``_default`` naming the default vault. Both tools read and
   write the same file, so vaults registered in jseeqret show up
   here and vice versa::

       {"_default": "work",
        "work": "E:/vaults/work/seeqret",
        "personal": "C:/Users/me/personal/seeqret"}
"""
import json
import os

DEFAULT_KEY = '_default'


def registry_path() -> str:
    return os.path.join(os.path.expanduser('~'), '.seeqret', 'vaults.json')


def read_registry() -> dict:
    """Read the registry, returning {} when it doesn't exist.
    """
    try:
        with open(registry_path(), encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_registry(reg: dict) -> None:
    path = registry_path()
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        os.makedirs(parent, mode=0o700)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(reg, indent=4))


def registry_add(name: str, path: str) -> None:
    """Register a vault. ``_default`` is a reserved name.
    """
    if name == DEFAULT_KEY:
        raise ValueError(f'{DEFAULT_KEY!r} is a reserved name')
    reg = read_registry()
    reg[name] = os.path.abspath(path)
    write_registry(reg)


def registry_remove(name: str) -> bool:
    """Unregister a vault (never touches the files). Returns True
       when a registration was removed.
    """
    if name == DEFAULT_KEY:
        return False
    reg = read_registry()
    if name not in reg:
        return False
    del reg[name]
    if reg.get(DEFAULT_KEY) == name:
        del reg[DEFAULT_KEY]
    write_registry(reg)
    return True


def registry_use(name: str) -> None:
    """Make *name* the default vault.
    """
    reg = read_registry()
    if name not in reg or name == DEFAULT_KEY:
        raise ValueError(f'unregistered vault: {name}')
    reg[DEFAULT_KEY] = name
    write_registry(reg)


def registry_list() -> list[dict]:
    """All registered vaults as ``[{name, path, is_default}]``.
    """
    reg = read_registry()
    default = reg.get(DEFAULT_KEY)
    return [dict(name=name, path=path, is_default=(name == default))
            for name, path in sorted(reg.items())
            if name != DEFAULT_KEY]


def registry_resolve(name: str) -> str | None:
    """The registered path for *name*, or None.
    """
    if name == DEFAULT_KEY:
        return None
    return read_registry().get(name)


def registry_default() -> str | None:
    """The name of the default vault, or None.
    """
    return read_registry().get(DEFAULT_KEY)


def active_vault_dir() -> str | None:
    """Resolve the active vault: registry default first, then the
       SEEQRET environment variable (mirrors jseeqret's
       get_active_vault_dir).
    """
    default = registry_default()
    if default:
        path = registry_resolve(default)
        if path:
            return path
    return os.environ.get('SEEQRET')
