from contextlib import contextmanager
import os
import textwrap
import click


def local_appdata_dir():
    """Get the application data directory.
    """
    return click.get_app_dir('seeqret', roaming=False)


def roaming_appdata_dir():
    """Get the application data directory.
    """
    return click.get_app_dir('seeqret', roaming=True)


def remove_file_if_exists(fname):
    """Remove a file if it exists.
    """
    if os.path.exists(fname):
        os.remove(fname)


def move_file_and_overwrite(src, dst):
    """Move a file. Remove the destination if it exists.
    """
    if os.path.exists(dst):
        os.remove(dst)
    os.rename(src, dst)


def write_file(fname, content):
    """Write content to a file.
    """
    with open(fname, 'w') as f:
        f.write(textwrap.dedent(content))


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

