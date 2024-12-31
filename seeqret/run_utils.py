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


def run(cmd, echo=True):
    if echo:
        click.secho(f"    > {cmd}", fg='blue')
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
        return name_buffer.value
    else:
        import pwd
        # username (e.g. thebjorn)
        return pwd.getpwuid(os.geteuid()).pw_name


if __name__ == '__main__':
    print(current_user())
