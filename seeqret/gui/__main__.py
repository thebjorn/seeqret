"""Entry point: ``python -m seeqret.gui``.
"""
import os
import sys

from PySide6.QtWidgets import QApplication

from ..vault_registry import active_vault_dir
from .main_window import MainWindow
from .theme import STYLESHEET
from .vault_facade import VaultFacade


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    # jseeqret-style resolution: registry default first, then the
    # SEEQRET env var. An uninitialized state lands on the
    # first-run view instead of erroring out.
    vault_dir = active_vault_dir()
    if vault_dir:
        os.environ['SEEQRET'] = vault_dir

    window = MainWindow(VaultFacade())
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
