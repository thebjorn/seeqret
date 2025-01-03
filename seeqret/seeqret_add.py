import click

from seeqret.storage.sqlite_storage import SqliteStorage


# def fetch_pubkey_from_url(url):
#     # FIXME: this does not provide a way to connect the user to the pubkey!
#     r = requests.get(url)
#     if r.status_code != 200:
#         ctx = None
#         try:
#             ctx = click.get_current_context()
#         except AttributeError:
#             # during testing we don't neccessarily have a context...
#             raise RuntimeError(f'Could not fetch pubkey from url: {url}')
#         ctx.fail(click.style(f'Failed to fetch public key: {url}', fg='red'))
#     click.secho('Public key fetched.', fg='green')
#     return r.text


# seeqret add user ...
def add_user(pubkey, username, email):
    click.secho(f'Adding user: {username} with email: {email}', fg='blue')

    storage = SqliteStorage()
    from seeqret.models import User
    users = storage.add_user(User(pubkey=pubkey, username=username, email=email))

    click.secho('User added:', fg='green')
    click.secho(f'    {users[0]}', fg='green')
