import os
from contextlib import contextmanager

import click


@contextmanager
def cd(path):
    """Change the current working directory.
    """
    old_dir = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_dir)


def run(cmd, echo=True):
    if echo:
        click.secho(f"    > {cmd}", fg='blue')
    res = os.popen(cmd).read()
    if echo:
        for line in res.split('\n'):
            click.secho(f"      {line}", fg='green')
    return res
