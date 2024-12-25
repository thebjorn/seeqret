import os
import textwrap
import click
import json

from seeqret.run_utils import run


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
        f.write(textwrap.dedent(content).rstrip() + '\n')


def read_file(fname):
    """Read content from a file.
    """
    with open(fname, 'r') as f:
        return f.read()


def read_json(fname):
    """Read json content from a file.
    """
    with open(fname, 'r') as f:
        return json.load(f)


def read_binary_file(fname):
    """Read content from a file.
    """
    with open(fname, 'rb') as f:
        return f.read()


def is_writable(dirname):
    """Check if a directory is writable.
    """
    return os.access(dirname, os.W_OK)


def is_readable(dirname):
    """Check if a directory is readable.
    """
    return os.access(dirname, os.R_OK)


def remove_directory(dirname):
    """Remove a directory, recursively.
    """
    if os.path.exists(dirname):
        for root, dirs, files in os.walk(dirname, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(dirname)


def write_binary_file(fname, content):
    """Write content to a file.
    """
    with open(fname, 'wb') as f:
        f.write(content)


def attrib_cmd(vault_dir, cmd=""):
    return run(f"attrib {cmd} {vault_dir}").strip()


def is_encrypted(dirname):
    """Check if a directory is encrypted.
    """
    if os.name == 'nt':
        return run(f"cipher /c {dirname}").find(f'E {dirname}') != -1
    return False
