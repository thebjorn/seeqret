import os
import sys
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


def get_seeqret_dir():
    if sys.platform == 'win32' or 'CI' in os.environ:
        return os.environ['SEEQRET']
    else:
        return '/srv/.seeqret'


def is_initialized():
    if 'SEEQRET' not in os.environ:
        return False
    sdir = get_seeqret_dir()
    if not os.path.exists(sdir):
        return False
    if not os.path.exists(os.path.join(sdir, 'seeqrets.db')):
        return False
    return True


@contextmanager
def seeqret_dir():
    old_dir = os.getcwd()
    os.chdir(get_seeqret_dir())
    try:
        yield
    finally:
        os.chdir(old_dir)


def run(cmd, echo=True, workdir='.'):
    if echo:
        click.secho(f"    > {cmd}", fg='blue')
    with cd(workdir):
        res = os.popen(cmd).read()
    if echo:
        for line in res.split('\n'):
            click.secho(f"      {line}", fg='green')
    return res


def current_user():
    if sys.platform == 'win32':
        import ctypes
        GetUserNameExW = ctypes.windll.secur32.GetUserNameExW
        # https://learn.microsoft.com/en-us/windows/win32/api/secext/ne-secext-extended_name_format # noqa
        sam_compatible = 2  # MACHINE|domain\username (e.g. MYPC\thebjorn)

        size = ctypes.pointer(ctypes.c_ulong(0))
        GetUserNameExW(sam_compatible, None, size)

        name_buffer = ctypes.create_unicode_buffer(size.contents.value)
        GetUserNameExW(sam_compatible, name_buffer, size)
        domain_name = name_buffer.value
        return domain_name.split('\\')[1]
    else:
        import pwd
        # username (e.g. thebjorn)
        return pwd.getpwuid(os.geteuid()).pw_name


if __name__ == '__main__':
    print(current_user())
