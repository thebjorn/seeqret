"""Click command group for ``seeqret pull ...``.

   Pull secrets from external systems into the local vault. Every ssh
   remote with a ``--get`` template (``seeqret remote add``) is
   available as ``seeqret pull <alias> KEY...``.
"""

import click

from .cli_remote_ssh import PullGroup


@click.group('pull', cls=PullGroup)
def pull():
    """Pull secrets from external systems into the vault.

    Any ssh remote registered with `seeqret remote add <alias> ...
    --get ...` is available as `seeqret pull <alias> KEY...`. Values
    go straight into the vault and are never printed.
    """
    pass
