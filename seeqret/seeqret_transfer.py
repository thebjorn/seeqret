import json
import os
import sys
from textwrap import dedent

import click
from nacl.exceptions import CryptoError

from .filterspec import FilterSpec
from .models import User, jason
from .seeqrypt.nacl_backend import (
    asymetric_decrypt_string, asymetric_encrypt_string, load_private_key,
)
from .storage.sqlite_storage import SqliteStorage


def unknown_user_error(username: str) -> click.ClickException:
    """Build a ClickException with helpful guidance for an unknown user.
    """
    cmd = lambda s: click.style(s, fg='green')  # noqa: E731
    cmd_blue = lambda s: click.style(s, fg='blue')  # noqa: E731
    return click.ClickException(
        click.style(f"Unknown user: '{username}'.", fg='bright_red') + "\n" + dedent(
            f"""
            Use
            - {cmd('seeqret users')} to list known users.
            - {cmd('seeqret add user')} to add a new user.
            - {cmd('seeqret edit user')} to edit an existing user.
            - {cmd('seeqret rm user')} to remove an existing user.

            The other user needs to send you their public key. They must run:

                > seeqret introduction
                Please add me to your vault!
                {cmd_blue('seeqret add user --username usr --email usr@.. --pubkey ThkU/1234...')}

            and send the command to you (can be pasted into an insecure channel like
            email). When you run the command, your vault will know about the new user
            (and their public key).
            """
        )
    )


def ambiguous_user_error(username: str,
                         candidates: list) -> click.ClickException:
    """Build a ClickException for a bare username matching several users.
    """
    cmd = lambda s: click.style(s, fg='green')  # noqa: E731
    names = '\n            '.join(
        f'- {cmd(u.username)} <{u.email}>' for u in candidates
    )
    return click.ClickException(
        click.style(f"Ambiguous user: '{username}'.", fg='bright_red')
        + "\n" + dedent(
            f"""
            The name matches more than one user:

            {names}

            Use the full user@host form to disambiguate
            ({cmd('seeqret users')} to list known users).
            """
        )
    )


def resolve_user(storage, name: str):
    """Resolve NAME to a user in the vault.

       Tries an exact username match first.  A bare name (no @host
       qualifier) falls back to matching a single qualified user, so
       existing vaults and habits keep working.  Raises a ClickException
       if the name is unknown or ambiguous.
    """
    users = storage.fetch_users()
    for user in users:
        if user.username == name:
            return user
    if '@' not in name:
        matches = [u for u in users if u.username.startswith(name + '@')]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ambiguous_user_error(name, matches)
    raise unknown_user_error(name)


def resolve_recipients(storage, names):
    """Expand the ``--to`` NAMES into an ordered, de-duplicated list of
       recipient usernames.

       Two special tokens are recognised:
       - ``self`` is passed through unchanged (the export layer maps it
         to the vault owner).
       - ``all`` expands to every known user *except* the vault owner.

       Any other name is resolved with :func:`resolve_user` (accepting a
       bare or qualified name).  Duplicates are removed while preserving
       first-seen order, so ``--to all --to bob`` exports to ``bob`` once.
    """
    admin = storage.fetch_admin()
    recipients = []
    seen = set()

    def add(name):
        if name not in seen:
            seen.add(name)
            recipients.append(name)

    for name in names:
        if name == 'self':
            add('self')
        elif name == 'all':
            for user in storage.fetch_users():
                if admin and user.username == admin.username:
                    continue
                add(user.username)
        else:
            add(resolve_user(storage, name).username)

    return recipients


def import_secrets(sender, file, value, serializer):
    storage = SqliteStorage()
    receiver = storage.fetch_admin()
    sender = resolve_user(storage, sender)

    s = serializer(
        sender=sender,
        receiver=receiver,
        receiver_private_key=load_private_key('private.key'),
    )
    secrets = s.load(file or value)
    for secret in secrets:
        storage.upsert_secret(secret)


def export_secrets(ctx, *, to: str, fspec: FilterSpec, serializer,
                   out=None, windows=False, linux=False, echo=True):
    """seeqret export <user>

       Exports secrets from a SQLite database, preparing them for secure
       transfer to the specified receiver. The function retrieves secrets,
       decrypts them with a symmetric key, then encrypts the values with
       asymmetric encryption for the receiver. Finally, it generates a
       signature for the exported secrets for authenticity and integrity.

       Parameters:
           to (str): The recipient's username or the string 'self'
                     indicating the administrator. Secrets will be encrypted
                     using the public key of the specified user or
                     administrator.

       Returns:
           dict: A dictionary structured to contain metadata of the transaction
                 including the sender, receiver, and encrypted secrets ready
                 for transfer, along with a signature.

       Raises:
           Various exceptions may arise during database connection issues,
           encryption/decryption processes, or key-loading operations,
           depending on implementation details not shown here.
    """
    storage = SqliteStorage()

    admin = storage.fetch_admin()
    if to == 'self':
        receiver = admin
    else:
        receiver = resolve_user(storage, to)

    s = serializer(
        sender=admin,
        receiver=receiver,
        sender_private_key=load_private_key('private.key'),
    )

    secrets = storage.fetch_secrets(**fspec.to_filterdict())
    system = sys.platform  # default to current system
    if windows:
        system = 'win32'
    if linux:
        system = 'linux'
    res = s.dumps(secrets, system)

    if out:
        click.echo(f"Writing secrets to: {out} ({os.path.join(ctx.obj['curdir'], out)})")
        with open(os.path.join(ctx.obj['curdir'], out), 'w') as f:
            f.write(res)
    elif echo:
        click.echo(res)
    return res


USERS_EXPORT_KIND = 'users'
USERS_EXPORT_VERSION = 1
USERS_SERIALIZERS = ('json-crypt', 'command')
# prefix of a ``-s command`` users value: users:<version>:<ciphertext>
USERS_COMMAND_PREFIX = 'users:'


def _users_for(storage, receiver):
    """Every user in the vault except RECEIVER, as plain dicts."""
    return [
        dict(username=u.username, email=u.email, pubkey=u.pubkey,
             name=u.name)
        for u in storage.fetch_users()
        if u.username != receiver.username
    ]


def _box(value, receiver) -> str:
    """NaCl Box VALUE (as ascii JSON) from the vault owner to RECEIVER."""
    return asymetric_encrypt_string(
        json.dumps(value, ensure_ascii=True, sort_keys=True),
        load_private_key('private.key'), receiver.public_key,
    )


def export_users(storage, *, to: str, serializer: str = 'json-crypt') -> str:
    """seeqret export users --to <user> [-s json-crypt|command]

       Serialize every user in the vault (except the recipient) so that
       only the recipient can read it.  Values are NaCl Boxes from the
       vault owner to the recipient, so they are also authenticated: the
       recipient knows the public keys came from the owner and were not
       swapped in transit.  Each user is a JSON object with ``username``,
       ``email``, ``pubkey`` and ``name``.

       ``json-crypt`` (version 1) is one JSON document with the whole
       list in a single Box::

           {
               "kind": "users",
               "version": 1,
               "from": {username, email, pubkey, ...},
               "to": {username, email, pubkey, ...},
               "users": "<base64 Box(json list of users)>"
           }

       ``command`` is one line per user that the recipient pastes into a
       terminal::

           seeqret load -u<owner> -scommand -vusers:1:<base64 Box(json user)>
    """
    if serializer not in USERS_SERIALIZERS:
        raise click.ClickException(
            f"Unknown users serializer: `{serializer}` "
            f"({', '.join(USERS_SERIALIZERS)})."
        )
    admin = storage.fetch_admin()
    receiver = admin if to == 'self' else resolve_user(storage, to)
    users = _users_for(storage, receiver)

    if serializer == 'command':
        return '\n'.join(
            f'seeqret load -u{admin.username} -scommand '
            f'-v{USERS_COMMAND_PREFIX}{USERS_EXPORT_VERSION}:'
            f'{_box(u, receiver)}'
            for u in users
        )

    return jason.dumps({
        'kind': USERS_EXPORT_KIND,
        'version': USERS_EXPORT_VERSION,
        'from': admin,
        'to': receiver,
        'users': _box(users, receiver),
    })


def is_users_export(text: str) -> bool:
    """True if TEXT was produced by :func:`export_users` (either format).
    """
    if not isinstance(text, str):
        return False
    if text.startswith(USERS_COMMAND_PREFIX):
        return True
    try:
        data = json.loads(text)
    except ValueError:
        return False
    return isinstance(data, dict) and data.get('kind') == USERS_EXPORT_KIND


def _check_version(version):
    if str(version) != str(USERS_EXPORT_VERSION):
        raise click.ClickException(
            f"Unsupported users export version: {version!r}."
        )


def import_users(sender: str, text: str):
    """Add the users in a ``seeqret export users`` export (json-crypt
       document or ``-s command`` value) to the vault.

       Users that already exist (same username) are skipped.  If an
       existing user's public key differs from the one in the export a
       warning is printed, but the vault is left unchanged.

       Returns ``(added, skipped)`` lists of usernames.
    """
    storage = SqliteStorage()
    receiver = storage.fetch_admin()
    sender = resolve_user(storage, sender)

    if text.startswith(USERS_COMMAND_PREFIX):
        version, _, cipher = text[len(USERS_COMMAND_PREFIX):].partition(':')
        single = True
    else:
        data = json.loads(text)
        version, cipher = data.get('version'), data.get('users')
        single = False
    _check_version(version)

    try:
        payload = json.loads(asymetric_decrypt_string(
            cipher, load_private_key('private.key'), sender.public_key,
        ))
    except (CryptoError, ValueError, TypeError):
        raise click.ClickException(
            f"Could not decrypt the users export. It must be exported "
            f"by {sender.username} to {receiver.username}."
        )

    added, skipped = [], []
    for u in ([payload] if single else payload):
        existing = storage.fetch_user(u['username'])
        if existing is not None:
            skipped.append(u['username'])
            if existing.pubkey != u['pubkey']:
                click.secho(
                    f"Warning: {u['username']} already exists with a "
                    f"different public key (kept the existing one).",
                    fg='yellow', err=True,
                )
            continue
        storage.add_user(User(
            username=u['username'], email=u['email'], pubkey=u['pubkey'],
            name=u.get('name'),
        ))
        added.append(u['username'])
    return added, skipped
