import click

@click.group()
def cli():
    print('Hello, world!')
    

@cli.command()
def generate():
    print('Generating a new key pair')


@cli.command()
def encrypt():
    print('Encrypting a message')


@cli.command()
def decrypt():
    print('Decrypting a message')
