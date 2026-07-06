"""Vault lifecycle widgets: switcher, create dialog, first-run pane
   (mirror jseeqret's VaultSwitcher + wizard create step).
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .vault_facade import VaultFacade
from .widgets import Banner, view_title


class CreateVaultDialog(QDialog):
    """Pick a parent directory + email; the vault is created at
       ``<parent>/seeqret`` and registered.
    """

    def __init__(self, facade: VaultFacade, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.created = None
        self.setWindowTitle('Create vault')
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        dir_row = QHBoxLayout()
        self.dir_edit = QLineEdit()
        dir_row.addWidget(self.dir_edit, 1)
        browse = QPushButton('Browse...')
        browse.setProperty('class', 'secondary')
        browse.clicked.connect(self.pick_dir)
        dir_row.addWidget(browse)
        form.addRow('Parent directory', dir_row)
        self.email_edit = QLineEdit()
        form.addRow('Email', self.email_edit)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(
            'registry name (default: directory name)')
        form.addRow('Vault name', self.name_edit)
        layout.addLayout(form)
        note = QLabel('The vault directory <parent>/seeqret is'
                      ' created, keys are generated, and the vault is'
                      ' registered and made active.')
        note.setProperty('class', 'muted')
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.do_create)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def pick_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, 'Vault parent directory')
        if path:
            self.dir_edit.setText(path)

    def do_create(self) -> None:
        parent_dir = self.dir_edit.text().strip()
        email = self.email_edit.text().strip()
        if not parent_dir or not email:
            QMessageBox.warning(self, 'Create vault',
                                'Directory and email are required.')
            return
        try:
            self.created = self.facade.create_vault(
                parent_dir, email,
                name=self.name_edit.text().strip() or None)
        except Exception as e:
            QMessageBox.critical(self, 'Create vault', str(e))
            return
        self.accept()


class VaultSwitcher(QWidget):
    """Registry-backed vault picker for the sidebar.
    """
    switched = Signal()

    def __init__(self, facade: VaultFacade, parent=None):
        super().__init__(parent)
        self.facade = facade
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        self.combo = QComboBox()
        self.combo.activated.connect(self.on_pick)
        layout.addWidget(self.combo)
        self._loading = False

    def refresh(self) -> None:
        self._loading = True
        self.combo.clear()
        vaults = self.facade.list_vaults()
        active_ix = 0
        for i, vault in enumerate(vaults):
            badge = ' [default]' if vault['is_default'] else ''
            if not vault['initialized']:
                badge += ' [not init]'
            self.combo.addItem(vault['name'] + badge, vault)
            if vault['active']:
                active_ix = i
        if not vaults:
            self.combo.addItem('(no registered vaults)', None)
        self.combo.addItem('+ create vault...', 'create')
        self.combo.addItem('+ register existing...', 'register')
        self.combo.setCurrentIndex(active_ix)
        self._loading = False

    def on_pick(self, index: int) -> None:
        if self._loading:
            return
        data = self.combo.itemData(index)
        if data == 'create':
            dlg = CreateVaultDialog(self.facade, self)
            if dlg.exec() == QDialog.Accepted and dlg.created:
                self.switched.emit()
            self.refresh()
        elif data == 'register':
            path = QFileDialog.getExistingDirectory(
                self, 'Existing vault directory (contains seeqrets.db)')
            if path:
                name, ok = _prompt_text(self, 'Register vault',
                                        'Registry name:')
                if ok and name:
                    self.facade.register_vault(name, path)
            self.refresh()
        elif isinstance(data, dict):
            try:
                self.facade.switch_vault(data['name'])
            except Exception as e:
                QMessageBox.critical(self, 'Switch vault', str(e))
                self.refresh()
                return
            self.switched.emit()
            self.refresh()


def _prompt_text(parent, title: str, label: str) -> tuple[str, bool]:
    from PySide6.QtWidgets import QInputDialog
    text, ok = QInputDialog.getText(parent, title, label)
    return text.strip(), ok


class FirstRunView(QWidget):
    """Shown instead of the main views when no vault is active.
    """

    def __init__(self, facade: VaultFacade, on_created, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.on_created = on_created
        layout = QVBoxLayout(self)
        layout.addStretch(1)
        layout.addWidget(view_title('Welcome to seeqret'))
        body = QLabel(
            'No vault is active. Create a new vault, or register an'
            ' existing one (a directory containing seeqrets.db and'
            ' the key files).')
        body.setProperty('class', 'muted')
        body.setWordWrap(True)
        layout.addWidget(body)
        self.banner = Banner()
        layout.addWidget(self.banner)
        row = QHBoxLayout()
        create_btn = QPushButton('Create vault...')
        create_btn.clicked.connect(self.do_create)
        row.addWidget(create_btn)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addStretch(2)

    def do_create(self) -> None:
        dlg = CreateVaultDialog(self.facade, self)
        if dlg.exec() == QDialog.Accepted and dlg.created:
            self.on_created()

    def refresh(self) -> None:
        pass
