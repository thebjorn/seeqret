"""Main window shell: sidebar navigation + stacked views.

   Mirrors jseeqret's ``App.svelte`` + ``Sidebar.svelte``: a fixed
   1000x700 window with a 220px sidebar driving a swapped content
   pane. Views re-query the facade every time they are shown (the
   Qt equivalent of jseeqret's ``refresh_key`` remounts).
"""
from datetime import datetime

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from .vault_facade import VaultFacade

MASK_CHAR = '•'


def mask_value(value: str) -> str:
    """Mask a secret value like jseeqret: first 2 chars + dots.
    """
    txt = str(value)
    return txt[:2] + MASK_CHAR * max(len(txt) - 2, 3)


def format_timestamp(unix_seconds: int | None) -> str:
    if not unix_seconds:
        return ''
    return datetime.fromtimestamp(unix_seconds).strftime('%Y-%m-%d %H:%M')


class SecretsModel(QAbstractTableModel):
    """Table model over the facade's decrypted secret dicts.

       Values are masked unless the row is in ``revealed``
       (toggled by double-clicking the value cell).
    """
    COLUMNS = ('App', 'Env', 'Key', 'Value', 'Type', 'Updated')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: list[dict] = []
        self.revealed: set[tuple] = set()

    def set_rows(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def row_ident(self, row: int) -> tuple:
        rec = self.rows[row]
        return (rec['app'], rec['env'], rec['key'])

    def toggle_reveal(self, row: int) -> None:
        ident = self.row_ident(row)
        self.revealed.symmetric_difference_update({ident})
        ix = self.index(row, 3)
        self.dataChanged.emit(ix, ix)

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.COLUMNS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        rec = self.rows[index.row()]
        col = index.column()
        if role == Qt.DisplayRole:
            if col == 0:
                return rec['app']
            if col == 1:
                return rec['env']
            if col == 2:
                return rec['key']
            if col == 3:
                value = str(rec['value'])
                if self.row_ident(index.row()) in self.revealed:
                    return value
                return mask_value(value)
            if col == 4:
                return rec['type']
            if col == 5:
                return format_timestamp(rec.get('updated_at'))
        return None


class UsersModel(QAbstractTableModel):
    COLUMNS = ('Name', 'Username', 'Email', 'Fingerprint')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: list[dict] = []

    def set_rows(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.COLUMNS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        rec = self.rows[index.row()]
        col = index.column()
        if col == 0:
            name = rec.get('name') or ''
            return f'{name} (owner)' if rec['is_owner'] else name
        if col == 1:
            return rec['username']
        if col == 2:
            return rec['email']
        if col == 3:
            return rec['fingerprint']
        return None


class SecretDialog(QDialog):
    """Add/edit dialog. In edit mode the identity fields are frozen
       (jseeqret rule: app:env:key is immutable, value-only edits).
    """

    def __init__(self, parent=None, secret: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle('Edit secret' if secret else 'Add secret')
        self.setMinimumWidth(420)
        form = QFormLayout(self)

        self.app_edit = QLineEdit(secret['app'] if secret else '*')
        self.env_edit = QLineEdit(secret['env'] if secret else '*')
        self.key_edit = QLineEdit(secret['key'] if secret else '')
        self.value_edit = QLineEdit(str(secret['value']) if secret else '')
        self.type_combo = QComboBox()
        self.type_combo.addItems(['str', 'int'])
        if secret:
            self.type_combo.setCurrentText(secret['type'])
            for w in (self.app_edit, self.env_edit,
                      self.key_edit, self.type_combo):
                w.setEnabled(False)

        form.addRow('App', self.app_edit)
        form.addRow('Env', self.env_edit)
        form.addRow('Key', self.key_edit)
        form.addRow('Value', self.value_edit)
        form.addRow('Type', self.type_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def result_dict(self) -> dict:
        return dict(
            app=self.app_edit.text().strip(),
            env=self.env_edit.text().strip(),
            key=self.key_edit.text().strip(),
            value=self.value_edit.text(),
            type=self.type_combo.currentText(),
        )


class SecretsView(QWidget):
    """The core screen: filter bar + sortable table + row actions.
    """

    def __init__(self, facade: VaultFacade, parent=None):
        super().__init__(parent)
        self.facade = facade
        layout = QVBoxLayout(self)

        title = QLabel('Secrets')
        title.setObjectName('view_title')
        layout.addWidget(title)

        bar = QHBoxLayout()
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(
            'filter, e.g.  myapp:prod:*  (app:env:key globs)')
        self.filter_edit.textChanged.connect(self.refresh)
        bar.addWidget(self.filter_edit, 1)

        add_btn = QPushButton('Add secret')
        add_btn.clicked.connect(self.add_secret)
        bar.addWidget(add_btn)
        edit_btn = QPushButton('Edit')
        edit_btn.setProperty('class', 'secondary')
        edit_btn.clicked.connect(self.edit_secret)
        bar.addWidget(edit_btn)
        copy_btn = QPushButton('Copy value')
        copy_btn.setProperty('class', 'secondary')
        copy_btn.clicked.connect(self.copy_value)
        bar.addWidget(copy_btn)
        del_btn = QPushButton('Delete')
        del_btn.setProperty('class', 'secondary')
        del_btn.clicked.connect(self.delete_secret)
        bar.addWidget(del_btn)
        layout.addLayout(bar)

        self.model = SecretsModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.table.doubleClicked.connect(self.on_double_click)
        layout.addWidget(self.table, 1)

        self.count_label = QLabel('')
        self.count_label.setProperty('class', 'muted')
        layout.addWidget(self.count_label)

        self.status_label = QLabel('')
        self.status_label.setProperty('class', 'mono')
        layout.addWidget(self.status_label)

    # -- helpers ------------------------------------------------------

    def current_secret(self) -> dict | None:
        ixs = self.table.selectionModel().selectedRows()
        if not ixs:
            return None
        return self.model.rows[ixs[0].row()]

    def flash(self, message: str) -> None:
        self.status_label.setText(message)
        QTimer.singleShot(1500, lambda: self.status_label.setText(''))

    def refresh(self) -> None:
        spec = self.filter_edit.text().strip() or '*:*:*'
        try:
            rows = self.facade.list_secrets(spec)
        except Exception as e:
            self.count_label.setText(f'error: {e}')
            return
        self.model.set_rows(rows)
        self.count_label.setText(f'{len(rows)} secrets')

    # -- actions ------------------------------------------------------

    def on_double_click(self, index) -> None:
        if index.column() == 3:
            self.model.toggle_reveal(index.row())

    def add_secret(self) -> None:
        dlg = SecretDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        rec = dlg.result_dict()
        if not rec['key']:
            QMessageBox.warning(self, 'Add secret', 'Key is required.')
            return
        try:
            self.facade.add_secret(**rec)
        except Exception as e:
            QMessageBox.critical(self, 'Add secret', str(e))
            return
        self.refresh()

    def edit_secret(self) -> None:
        rec = self.current_secret()
        if not rec:
            return
        dlg = SecretDialog(self, secret=rec)
        if dlg.exec() != QDialog.Accepted:
            return
        new = dlg.result_dict()
        self.facade.update_secret_value(
            app=rec['app'], env=rec['env'], key=rec['key'],
            value=new['value'], type=rec['type'])
        self.refresh()

    def copy_value(self) -> None:
        rec = self.current_secret()
        if not rec:
            return
        QGuiApplication.clipboard().setText(str(rec['value']))
        self.flash(f"copied {rec['app']}:{rec['env']}:{rec['key']} ✓")

    def delete_secret(self) -> None:
        rec = self.current_secret()
        if not rec:
            return
        ident = f"{rec['app']}:{rec['env']}:{rec['key']}"
        answer = QMessageBox.question(
            self, 'Delete secret', f'Delete {ident}?')
        if answer != QMessageBox.Yes:
            return
        self.facade.remove_secret(rec['app'], rec['env'], rec['key'])
        self.refresh()


class UsersView(QWidget):
    def __init__(self, facade: VaultFacade, parent=None):
        super().__init__(parent)
        self.facade = facade
        layout = QVBoxLayout(self)
        title = QLabel('Users')
        title.setObjectName('view_title')
        layout.addWidget(title)

        self.model = UsersModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        layout.addWidget(self.table, 1)

    def refresh(self) -> None:
        self.model.set_rows(self.facade.list_users())


def make_card(title: str, body: str, big: bool = False) -> QFrame:
    card = QFrame()
    card.setProperty('class', 'card')
    layout = QVBoxLayout(card)
    body_label = QLabel(body)
    if big:
        body_label.setProperty('class', 'stat_number')
    else:
        body_label.setProperty('class', 'mono')
    body_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    title_label = QLabel(title)
    title_label.setProperty('class', 'muted')
    layout.addWidget(body_label)
    layout.addWidget(title_label)
    return card


class DashboardView(QWidget):
    def __init__(self, facade: VaultFacade, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.layout = QVBoxLayout(self)

    def refresh(self) -> None:
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                child = item.layout()
                while child.count():
                    sub = child.takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        title = QLabel('Dashboard')
        title.setObjectName('view_title')
        self.layout.addWidget(title)

        status = self.facade.vault_status()
        n_secrets = len(self.facade.list_secrets())
        n_users = len(self.facade.list_users())

        cards = QHBoxLayout()
        cards.addWidget(make_card('secrets', str(n_secrets), big=True))
        cards.addWidget(make_card('users', str(n_users), big=True))
        cards.addWidget(make_card('owner', status['owner'] or '-'))
        self.layout.addLayout(cards)

        info = make_card(
            'vault',
            f"dir: {status['vault_dir']}\n"
            f"user: {status['current_user']}\n"
            f"version: {status['version']}")
        self.layout.addWidget(info)
        self.layout.addStretch(1)


class IntroductionView(QWidget):
    def __init__(self, facade: VaultFacade, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.layout = QVBoxLayout(self)

    def refresh(self) -> None:
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        title = QLabel('Introduction')
        title.setObjectName('view_title')
        self.layout.addWidget(title)

        intro = self.facade.introduction()
        if not intro:
            warn = QLabel('You are not a registered user of this vault.')
            warn.setProperty('class', 'muted')
            self.layout.addWidget(warn)
            self.layout.addStretch(1)
            return

        fp = QLabel(intro['fingerprint'])
        fp.setObjectName('fingerprint')
        self.layout.addWidget(fp)

        for field in ('username', 'name', 'email', 'pubkey'):
            if intro.get(field):
                self.layout.addWidget(
                    make_card(field, str(intro[field])))

        copy_btn = QPushButton('Copy "add user" command')
        copy_btn.clicked.connect(
            lambda: QGuiApplication.clipboard().setText(
                intro['add_command']))
        self.layout.addWidget(copy_btn)
        self.layout.addStretch(1)


class PlaceholderView(QWidget):
    """Stub for views not in the prototype (Export/Import/Onboarding).
    """

    def __init__(self, name: str, note: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel(name)
        title.setObjectName('view_title')
        layout.addWidget(title)
        body = QLabel(note)
        body.setProperty('class', 'muted')
        body.setWordWrap(True)
        layout.addWidget(body)
        layout.addStretch(1)

    def refresh(self) -> None:
        pass


class MainWindow(QMainWindow):
    VIEWS = (
        ('Dashboard', 'dashboard'),
        ('Secrets', 'secrets'),
        ('Users', 'users'),
        ('Export', 'export'),
        ('Import', 'import'),
        ('Introduction', 'introduction'),
    )

    def __init__(self, facade: VaultFacade):
        super().__init__()
        self.facade = facade
        self.setWindowTitle('seeqret')
        self.setFixedSize(1000, 700)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar_box = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_box)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        sidebar_box.setFixedWidth(220)

        status = facade.vault_status()
        brand = QLabel(f"seeqret <span style='color:#a3adc2;font-size:11px'>"
                       f"v{status['version']}</span>")
        brand.setObjectName('brand')
        sidebar_layout.addWidget(brand)

        self.nav = QListWidget()
        self.nav.setObjectName('sidebar')
        for label, _ in self.VIEWS:
            self.nav.addItem(label)
        self.nav.currentRowChanged.connect(self.switch_view)
        sidebar_layout.addWidget(self.nav, 1)

        footer = QLabel(f"● {status['current_user']}\n"
                        f"{status['vault_dir']}")
        footer.setObjectName('sidebar_footer')
        footer.setWordWrap(True)
        sidebar_layout.addWidget(footer)

        self.stack = QStackedWidget()
        stub_note = ('Not part of the prototype -- see '
                     'documentation/pyside6-gui/index.md, phase 2.')
        self.views = [
            DashboardView(facade),
            SecretsView(facade),
            UsersView(facade),
            PlaceholderView('Export', stub_note),
            PlaceholderView('Import', stub_note),
            IntroductionView(facade),
        ]
        for view in self.views:
            container = QWidget()
            wrap = QVBoxLayout(container)
            wrap.setContentsMargins(24, 16, 24, 16)
            wrap.addWidget(view)
            self.stack.addWidget(container)

        root_layout.addWidget(sidebar_box)
        root_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.nav.setCurrentRow(0)

    def switch_view(self, row: int) -> None:
        self.views[row].refresh()
        self.stack.setCurrentIndex(row)
