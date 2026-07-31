"""An ssh remote target (alias -> host + command templates).
"""

from dataclasses import dataclass


@dataclass
class Remote:
    """A named ssh target that secrets can be pushed to / verified on.

       ``set_cmd`` and ``get_cmd`` are remote command templates with
       ``{key}``/``{value}`` placeholders, e.g.::

           source /srv/bin/go dkpw set -k {key} --stdin
           source /srv/bin/go dkpw get {key} -s

       Placeholders are substituted with shell-quoted values, so the
       templates must not add their own quotes. A ``set_cmd`` without
       a ``{value}`` placeholder (like the one above) receives the
       value on stdin instead -- preferable, since command-line
       arguments are visible in ``ps`` on the remote host.
       ``get_cmd`` is optional; without it the remote is push-only.
    """
    alias: str
    username: str
    hostname: str
    set_cmd: str
    get_cmd: str | None = None

    @property
    def userhost(self) -> str:
        return f'{self.username}@{self.hostname}'

    @property
    def value_via_stdin(self) -> bool:
        return '{value}' not in self.set_cmd
