import os

import click

from seeqret import cd, seeqret_add


@click.command()
@click.argument('name')
@click.argument('value')
@click.option('--app', default='*', show_default=True,
              help='The app to add the secret to')
@click.option('--env', default='*', show_default=True,
              help='The env(ironment) to add the secret to (e.g. dev/prod)')
def key(name: str, value: str, app: str = None, env: str = None):  # noqa: F811
    """Add a new NAME -> VALUE mapping.

       You can (should) specify the app and environment properties when adding
       a new mapping.
    """
    print("KEY::")
    click.echo(
        f'Adding a new key: {name}, value: {value}, app: {app}, env: {env}'
    )

    with cd(os.environ['SEEQRET']):
        print("CALLING:seeqret_add.add_key", name, value, app, env)
        seeqret_add.add_key(name, value, app, env)
