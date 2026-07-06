"""Neutral exception types shared by the CLI and the GUI.

   ``SeeqretError`` subclasses ``click.ClickException`` so the CLI
   keeps rendering these exactly as before (Click catches them and
   prints the styled message), while non-CLI front ends catch
   ``SeeqretError`` and display the ANSI-free ``plain`` message.
"""
import click


class SeeqretError(click.ClickException):
    """Base error for seeqret operations.

       ``message`` may contain click styling for terminal display;
       ``plain`` is a short, style-free version for GUIs.
    """

    def __init__(self, message: str, plain: str | None = None):
        super().__init__(message)
        self.plain = plain or click.unstyle(message)


class UnknownUserError(SeeqretError):
    """A username that doesn't resolve to any user in the vault.
    """

    def __init__(self, message: str, username: str):
        super().__init__(message, plain=f"Unknown user: '{username}'.")
        self.username = username


class AmbiguousUserError(SeeqretError):
    """A bare username matching more than one qualified user.
    """

    def __init__(self, message: str, username: str, candidates: list):
        names = ', '.join(u.username for u in candidates)
        super().__init__(
            message,
            plain=f"Ambiguous user: '{username}' matches {names}.")
        self.username = username
        self.candidates = candidates
