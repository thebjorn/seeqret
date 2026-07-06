"""Slack transport view + team-lead onboarding panel (mirror
   jseeqret's SlackStatusCard/OnboardingView).
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .vault_facade import VaultFacade
from .widgets import (
    Banner,
    fingerprint_label,
    make_card,
    status_dot,
    view_title,
)
from .worker import call_async


class ChannelPickDialog(QDialog):
    def __init__(self, channels: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle('Pick the exchange channel')
        layout = QVBoxLayout(self)
        self.combo = QComboBox()
        default_ix = 0
        for i, c in enumerate(channels):
            self.combo.addItem(f"#{c['name']}", c)
            if c['name'] == 'seeqrets':
                default_ix = i
        self.combo.setCurrentIndex(default_ix)
        layout.addWidget(self.combo)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def chosen(self) -> dict:
        return self.combo.currentData()


class SlackView(QWidget):
    """Status card + login/logout/attest/selftest controls.
    """

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
                sub = item.layout()
                while sub.count():
                    inner = sub.takeAt(0)
                    if inner.widget():
                        inner.widget().deleteLater()

        self.layout.addWidget(view_title('Slack'))
        self.banner = Banner()
        self.layout.addWidget(self.banner)

        status = self.facade.slack_status()
        head = QLabel(
            f"{status_dot(status['ready'])} "
            + ('transport ready' if status['ready']
               else 'transport not ready'))
        head.setTextFormat(Qt.RichText)
        self.layout.addWidget(head)

        if status['logged_in']:
            token_age = status['token_age_days']
            mfa_age = status['mfa_age_days']
            self.layout.addWidget(make_card('session', (
                f"team: {status['team_name'] or '?'}\n"
                f"user: {status['user_id'] or '?'}\n"
                f"channel: #{status['channel_name'] or '?'}\n"
                f"token age: "
                f"{token_age if token_age is not None else '?'} days\n"
                f"MFA attested: "
                f"{str(mfa_age) + ' days ago' if mfa_age is not None else 'NO'}"
            )))
        if status['problems']:
            self.layout.addWidget(make_card(
                'problems', '\n'.join(status['problems'])))

        row = QHBoxLayout()
        if not status['logged_in']:
            login_btn = QPushButton('Log in to Slack')
            login_btn.clicked.connect(self.do_login)
            row.addWidget(login_btn)
        else:
            attest_btn = QPushButton('Attest SSO + MFA')
            attest_btn.setProperty('class', 'secondary')
            attest_btn.clicked.connect(self.do_attest)
            row.addWidget(attest_btn)
            selftest_btn = QPushButton('Test transport')
            selftest_btn.setProperty('class', 'secondary')
            selftest_btn.clicked.connect(self.do_selftest)
            row.addWidget(selftest_btn)
            logout_btn = QPushButton('Log out')
            logout_btn.setProperty('class', 'secondary')
            logout_btn.clicked.connect(self.do_logout)
            row.addWidget(logout_btn)
        row.addStretch(1)
        self.layout.addLayout(row)
        self.layout.addStretch(1)

    def do_login(self) -> None:
        self.banner.show_message(
            'A browser window opens for Slack OAuth; waiting for the'
            ' redirect...', 'info')
        call_async(self, self.facade.slack_login,
                   self._login_done, self._error)

    def _login_done(self, channels: list[dict]) -> None:
        if not channels:
            self.banner.show_message(
                'No private channels found. Create #seeqrets, invite'
                ' yourself, and log in again.', 'error')
            return
        dlg = ChannelPickDialog(channels, self)
        if dlg.exec() == QDialog.Accepted and dlg.chosen:
            self.facade.slack_set_channel(dlg.chosen['id'],
                                          dlg.chosen['name'])
        self.refresh()

    def do_attest(self) -> None:
        self.facade.slack_attest_mfa()
        self.refresh()

    def do_selftest(self) -> None:
        self.banner.show_message('Running transport selftest...', 'info')
        call_async(self, self.facade.slack_selftest,
                   self._selftest_done, self._error)

    def _selftest_done(self, result: dict) -> None:
        if result['ok']:
            self.banner.show_message(
                'Selftest OK: sent, received, and deleted a loopback'
                ' message.', 'success')
        else:
            self.banner.show_message(
                f"Selftest failed: {result.get('error')}", 'error')

    def do_logout(self) -> None:
        self.facade.slack_logout()
        self.refresh()

    def _error(self, message: str) -> None:
        self.banner.show_message(message, 'error')


class ApproveDialog(QDialog):
    """The OOB fingerprint ceremony gate for approving a new user.
    """

    def __init__(self, row: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Approve {row['email']}")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"User {row.get('username')} introduced themselves with"
            ' this key fingerprint:'))
        layout.addWidget(fingerprint_label(row.get('fingerprint') or '?'))
        layout.addWidget(QLabel(
            'Verify it OUT-OF-BAND (voice call, in person -- not via'
            ' Slack) before approving.'))
        self.verified_box = QCheckBox(
            'I verified this fingerprint on a voice call')
        layout.addWidget(self.verified_box)
        form = QFormLayout()
        self.fp_edit = QLineEdit()
        form.addRow('Type the fingerprint back', self.fp_edit)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def result_tuple(self) -> tuple[bool, str]:
        return self.verified_box.isChecked(), self.fp_edit.text().strip()


class OnboardingView(QWidget):
    """Team-lead panel: invite, poll, approve.
    """

    def __init__(self, facade: VaultFacade, parent=None):
        super().__init__(parent)
        self.facade = facade
        layout = QVBoxLayout(self)
        layout.addWidget(view_title('Onboarding'))
        self.banner = Banner()
        layout.addWidget(self.banner)

        form = QHBoxLayout()
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText('new user email')
        form.addWidget(self.email_edit, 1)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText('display name (optional)')
        form.addWidget(self.name_edit, 1)
        self.project_edit = QLineEdit()
        self.project_edit.setPlaceholderText('project filter, e.g. myapp:*:*')
        form.addWidget(self.project_edit, 1)
        invite_btn = QPushButton('Invite')
        invite_btn.clicked.connect(self.do_invite)
        form.addWidget(invite_btn)
        layout.addLayout(form)

        row = QHBoxLayout()
        poll_btn = QPushButton('Poll for replies')
        poll_btn.setProperty('class', 'secondary')
        poll_btn.clicked.connect(self.do_poll)
        row.addWidget(poll_btn)
        approve_btn = QPushButton('Approve selected')
        approve_btn.clicked.connect(self.do_approve)
        row.addWidget(approve_btn)
        row.addStretch(1)
        layout.addLayout(row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ['Email', 'Name', 'Username', 'Fingerprint', 'Project',
             'State'])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table, 1)
        self._rows = []

    def refresh(self) -> None:
        self.banner.clear_message()
        try:
            self._rows = self.facade.onboard_list()
        except Exception as e:
            self.banner.show_message(str(e), 'error')
            self._rows = []
        self.table.setRowCount(len(self._rows))
        for i, row in enumerate(self._rows):
            for col, key in enumerate(
                    ('email', 'name', 'username', 'fingerprint',
                     'project_filter', 'state')):
                item = QTableWidgetItem(str(row.get(key) or ''))
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table.setItem(i, col, item)

    def selected_row(self) -> dict | None:
        ixs = self.table.selectionModel().selectedRows()
        return self._rows[ixs[0].row()] if ixs else None

    def do_invite(self) -> None:
        email = self.email_edit.text().strip()
        if not email:
            self.banner.show_message('Email is required.', 'error')
            return
        self.banner.show_message(f'Inviting {email}...', 'info')
        call_async(
            self,
            lambda: self.facade.onboard_invite(
                email,
                self.project_edit.text().strip() or None,
                self.name_edit.text().strip() or None),
            lambda r: (self.banner.show_message(
                f"Invited {r['email']}.", 'success'), self.refresh()),
            self._error)

    def do_poll(self) -> None:
        self.banner.show_message('Polling Slack...', 'info')
        call_async(self, self.facade.onboard_poll,
                   self._poll_done, self._error)

    def _poll_done(self, events: list[dict]) -> None:
        if events:
            self.banner.show_message(
                '; '.join(f"{e['kind']}: {e.get('email')}"
                          for e in events), 'success')
        else:
            self.banner.show_message('No new onboarding traffic.',
                                     'info')
        self.refresh()

    def do_approve(self) -> None:
        row = self.selected_row()
        if not row:
            self.banner.show_message('Select an onboarding row first.',
                                     'error')
            return
        if row['state'] not in ('introduced', 'approved',
                                'provisioned'):
            self.banner.show_message(
                f"'{row['state']}' rows cannot be approved"
                ' (need an introduction first).', 'error')
            return
        dlg = ApproveDialog(row, self)
        if dlg.exec() != QDialog.Accepted:
            return
        verified, fp = dlg.result_tuple
        self.banner.show_message('Approving and provisioning...', 'info')
        call_async(
            self,
            lambda: self.facade.onboard_approve(row['email'],
                                                verified, fp),
            lambda r: (self.banner.show_message(
                f"Provisioned {r['email']}: {r['users_sent']} user(s),"
                f" {r['secrets_sent']} secret(s),"
                f" {r['broadcasts']} broadcast(s).", 'success'),
                self.refresh()),
            self._error)

    def _error(self, message: str) -> None:
        self.banner.show_message(message, 'error')
