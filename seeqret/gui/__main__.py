"""Entry point: ``python -m seeqret.gui``.
"""
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from ..run_utils import is_initialized
from .main_window import MainWindow
from .theme import STYLESHEET
from .vault_facade import VaultFacade


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    if not is_initialized():
        QMessageBox.critical(
            None, 'seeqret',
            'No initialized vault found.\n\n'
            'Set the SEEQRET environment variable to your vault '
            'directory (and run `seeqret init` first if needed).')
        return 1

    window = MainWindow(VaultFacade())
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
