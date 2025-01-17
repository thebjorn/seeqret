import click

from seeqret.serializers.serializer import SERIALIZERS
from .filterspec import FilterSpec
from .models import Secret
from .storage.sqlite_storage import SqliteStorage
from .run_utils import seeqret_dir


@click.command()
@click.pass_context
@click.argument('name')
@click.argument('value')
@click.option('--app', default='*', show_default=True,
              help='The app to add the secret to')
@click.option('--env', default='*', show_default=True,
              help='The env(ironment) to add the secret to (e.g. dev/prod)')
def key(ctx, name: str, value: str, app: str = None, env: str = None):  # noqa: F811
    """Add a new NAME -> VALUE mapping.

       You can (should) specify the app and environment properties when adding
       a new mapping.
    """
    if ':' in name or ':' in app or ':' in env:
        ctx.fail(click.style(
            'Colon `:` is not valid in key, app, or env', fg='red'
        ))
    click.secho(
        f'Adding a new key: {name}, value: {value}, app: {app}, env: {env}',
        fg='blue'
    )

    with seeqret_dir():
        storage = SqliteStorage()
        fspec = FilterSpec(f'{app}:{env}:{name}')
        secrets = storage.fetch_secrets(**fspec.to_filterdict())
        if secrets:
            ctx.fail(click.style(
                f'Secret {", ".join(s.key for s in secrets)} already exists!',
                fg='red'
            ))
        secret = Secret(
            app=app,
            env=env,
            key=name,
            plaintext_value=value,
            type='str'
        )
        storage.add_secret(secret)

        # verify that it worked
        secrets = storage.fetch_secrets(app=app, env=env, key=name)
        if secrets:
            click.secho(
                f'..successfully added: {app}:{env}[{key}]', fg='green'
            )
        else:
            ctx.fail(click.style(
                f'Error: {app}:{env}[{key}] not written to database', fg='red'
            ))


@click.command()
@click.option('--app', default='*', show_default=True,
              help='The app to add the secret to')
@click.option('--env', default='*', show_default=True,
              help='The env(ironment) to add the secret to (e.g. dev/prod)')
@click.argument('file', type=click.File('r'))
def file(app, env, file):
    """Add a new FILE to the vault (.env file format).
    """
    serializer_cls = SERIALIZERS.get('env')
    serializer = serializer_cls()
    with seeqret_dir():
        storage = SqliteStorage()
        secrets = serializer.load(file.read(), app=app, env=env)
        for secret in secrets:
            storage.add_secret(secret)
