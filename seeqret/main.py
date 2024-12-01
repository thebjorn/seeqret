import click

from . import seeqret_init


@click.group()
def cli():
    pass


@cli.command()
@click.option('--dir', default='.', help='Directory to initialize seeqret in')
def init():
    print('Initializing a new key pair')
    seeqret_init.secrets_init()


@cli.command()
def generate():
    print('Generating a new key pair')


@cli.command()
def encrypt():
    print('Encrypting a message')


@cli.command()
def decrypt():
    print('Decrypting a message')
