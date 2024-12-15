import os


class Context:
    """Execution environment context."""

    def __init__(self, vault_dir=None):
        self.vault_dir = vault_dir
        self.user = f"{os.environ['USERDOMAIN']}\\{os.environ['USERNAME']}"
