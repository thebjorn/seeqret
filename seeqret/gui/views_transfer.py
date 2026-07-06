"""Export and Import views (mirror jseeqret's ExportView/ImportView).
"""
import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QButtonGroup,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .vault_facade import VaultFacade
from .widgets import Banner, Segmented, format_timestamp, view_title
from .worker import call_async


class ExportView(QWidget):
    """Pick recipients (grouped by display name), filter, format,
       and output mode; preview before sending.
    """

    def __init__(self, facade: VaultFacade, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.recipient_boxes: list[tuple[QCheckBox, list[str]]] = []
        layout = QVBoxLayout(self)
        layout.addWidget(view_title('Export'))

        self.banner = Banner()
        layout.addWidget(self.banner)

        self.recipients_box = QVBoxLayout()
        recipients_label = QLabel('Recipients')
        recipients_label.setProperty('class', 'muted')
        layout.addWidget(recipients_label)
        layout.addLayout(self.recipients_box)

        form = QHBoxLayout()
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText('filter, e.g. myapp:prod:*')
        self.filter_edit.textChanged.connect(self.update_preview)
        form.addWidget(self.filter_edit, 1)
        self.serializer_combo = QComboBox()
        form.addWidget(self.serializer_combo)
        self.system = Segmented(['auto', 'windows', 'linux'])
        form.addWidget(self.system)
        layout.addLayout(form)

        out_row = QHBoxLayout()
        self.output_mode = Segmented(['Clipboard', 'File', 'Slack'])
        out_row.addWidget(self.output_mode)
        out_row.addStretch(1)
        self.export_btn = QPushButton('Export')
        self.export_btn.clicked.connect(self.do_export)
        out_row.addWidget(self.export_btn)
        layout.addLayout(out_row)

        self.preview_label = QLabel('')
        self.preview_label.setProperty('class', 'muted')
        layout.addWidget(self.preview_label)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

    def refresh(self) -> None:
        self.banner.clear_message()
        self.serializer_combo.clear()
        self.serializer_combo.addItems(self.facade.serializers())
        self.serializer_combo.setCurrentText('json-crypt')

        while self.recipients_box.count():
            item = self.recipients_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.recipient_boxes = []
        owner = (self.facade.vault_status().get('owner') or '')
        for group in self.facade.recipients_grouped():
            members = group['members']
            suffix = '' if len(members) == 1 \
                else f" ({len(members)} identities)"
            label = group['label'] + suffix
            if members == [owner]:
                label += '  [self]'
            box = QCheckBox(label)
            self.recipients_box.addWidget(box)
            self.recipient_boxes.append((box, members))
        self.update_preview()

    def selected_recipients(self) -> list[str]:
        res = []
        for box, members in self.recipient_boxes:
            if box.isChecked():
                res.extend(members)
        return res

    def update_preview(self) -> None:
        try:
            rows = self.facade.matching_secrets(
                self.filter_edit.text().strip())
        except Exception as e:
            self.preview_label.setText(f'filter error: {e}')
            return
        self.preview_label.setText(f'{len(rows)} matching secret(s)')

    def do_export(self) -> None:
        self.banner.clear_message()
        recipients = self.selected_recipients()
        if not recipients:
            self.banner.show_message('Pick at least one recipient.',
                                     'error')
            return
        mode = self.output_mode.value
        system = self.system.value
        kwargs = dict(
            to=recipients,
            filterspec=self.filter_edit.text().strip() or '*:*:*',
            serializer=self.serializer_combo.currentText(),
            system=None if system == 'auto' else
            ('win32' if system == 'windows' else 'linux'),
        )
        if mode == 'Slack':
            self.export_btn.setEnabled(False)
            call_async(
                self,
                lambda: self.facade.send_secrets_slack(
                    to=kwargs['to'], filterspec=kwargs['filterspec']),
                self._slack_done, self._slack_failed)
            return
        try:
            result = self.facade.export_secrets(**kwargs)
        except Exception as e:
            self.banner.show_message(str(e), 'error')
            return
        outputs = [r['output'] for r in result['results']]
        self.output.setPlainText('\n\n'.join(
            f"# -> {r['username']}\n{r['output']}"
            for r in result['results']))
        if mode == 'Clipboard':
            QGuiApplication.clipboard().setText('\n\n'.join(outputs))
            self.banner.show_message(
                f"Copied export for {len(outputs)} recipient(s)"
                ' to the clipboard.', 'success')
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, 'Save export', 'seeqret-export.json')
            if not path:
                return
            for i, rec in enumerate(result['results']):
                target = path if len(result['results']) == 1 else \
                    path.replace('.json', f"-{rec['username']}.json")
                with open(target, 'w', encoding='utf-8') as f:
                    f.write(rec['output'])
            self.banner.show_message(f'Wrote {path}', 'success')

    def _slack_done(self, results) -> None:
        self.export_btn.setEnabled(True)
        ok = [r for r in results if r.get('ok')]
        failed = [r for r in results if not r.get('ok')]
        msg = f'Sent to {len(ok)} recipient(s) via Slack.'
        if failed:
            msg += ' Failed: ' + '; '.join(
                f"{r['username']}: {r.get('error')}" for r in failed)
        self.banner.show_message(msg, 'error' if failed else 'success')

    def _slack_failed(self, message: str) -> None:
        self.export_btn.setEnabled(True)
        self.banner.show_message(message, 'error')


class ImportView(QWidget):
    """Two-phase import: preview -> per-conflict Mine/Theirs -> apply.
    """

    def __init__(self, facade: VaultFacade, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.conflict_groups: list[tuple[str, QButtonGroup]] = []
        layout = QVBoxLayout(self)
        layout.addWidget(view_title('Import'))

        self.banner = Banner()
        layout.addWidget(self.banner)

        form = QHBoxLayout()
        self.sender_combo = QComboBox()
        form.addWidget(self.sender_combo, 1)
        self.serializer_combo = QComboBox()
        form.addWidget(self.serializer_combo)
        self.input_mode = Segmented(['Paste', 'File'])
        self.input_mode.group.buttonClicked.connect(
            lambda _: self._sync_input_mode())
        form.addWidget(self.input_mode)
        self.browse_btn = QPushButton('Browse...')
        self.browse_btn.setProperty('class', 'secondary')
        self.browse_btn.clicked.connect(self.pick_file)
        form.addWidget(self.browse_btn)
        layout.addLayout(form)

        self.paste_edit = QPlainTextEdit()
        self.paste_edit.setPlaceholderText(
            'Paste an exported payload here...')
        layout.addWidget(self.paste_edit, 1)

        row = QHBoxLayout()
        self.preview_btn = QPushButton('Preview import')
        self.preview_btn.clicked.connect(self.do_preview)
        row.addWidget(self.preview_btn)
        row.addStretch(1)
        layout.addLayout(row)

        # conflict resolution UI (hidden until needed)
        self.conflict_table = QTableWidget(0, 5)
        self.conflict_table.setHorizontalHeaderLabels(
            ['Secret', 'Mine', 'Theirs', 'Mine ts', 'Theirs ts'])
        self.conflict_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.conflict_table.verticalHeader().setVisible(False)
        self.conflict_table.setVisible(False)
        layout.addWidget(self.conflict_table, 2)

        bulk = QHBoxLayout()
        self.keep_mine_btn = QPushButton('Keep all mine')
        self.take_theirs_btn = QPushButton('Take all theirs')
        self.take_newer_btn = QPushButton('Take newer')
        for btn, decision in ((self.keep_mine_btn, 0),
                              (self.take_theirs_btn, 1)):
            btn.setProperty('class', 'secondary')
            btn.clicked.connect(
                lambda _=None, d=decision: self.bulk_resolve(d))
        self.take_newer_btn.setProperty('class', 'secondary')
        self.take_newer_btn.clicked.connect(self.bulk_newer)
        self.apply_btn = QPushButton('Apply merge')
        self.apply_btn.clicked.connect(self.do_apply)
        for w in (self.keep_mine_btn, self.take_theirs_btn,
                  self.take_newer_btn):
            bulk.addWidget(w)
        bulk.addStretch(1)
        bulk.addWidget(self.apply_btn)
        self.bulk_row = QWidget()
        self.bulk_row.setLayout(bulk)
        self.bulk_row.setVisible(False)
        layout.addWidget(self.bulk_row)
        self._conflicts = []

    def refresh(self) -> None:
        self.banner.clear_message()
        self.sender_combo.clear()
        self.sender_combo.addItem('(from payload)', '')
        for user in self.facade.list_users():
            self.sender_combo.addItem(user['username'],
                                      user['username'])
        self.serializer_combo.clear()
        self.serializer_combo.addItems(self.facade.serializers())
        self.serializer_combo.setCurrentText('json-crypt')
        self._hide_conflicts()

    def _sync_input_mode(self) -> None:
        paste = self.input_mode.value == 'Paste'
        self.paste_edit.setVisible(paste)
        self.browse_btn.setVisible(not paste)

    def pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Import file')
        if path:
            with open(path, encoding='utf-8') as f:
                self.paste_edit.setPlainText(f.read())
            self.banner.show_message(f'Loaded {path}', 'info')

    def _hide_conflicts(self) -> None:
        self.conflict_table.setRowCount(0)
        self.conflict_table.setVisible(False)
        self.bulk_row.setVisible(False)
        self.conflict_groups = []
        self._conflicts = []

    def do_preview(self) -> None:
        self.banner.clear_message()
        content = self.paste_edit.toPlainText().strip()
        if not content:
            self.banner.show_message('Nothing to import.', 'error')
            return
        try:
            preview = self.facade.import_preview(
                content=content,
                from_user=self.sender_combo.currentData() or None,
                serializer=self.serializer_combo.currentText(),
            )
        except Exception as e:
            self.banner.show_message(str(e), 'error')
            return
        if not preview['needs_resolution']:
            result = self.facade.import_apply()
            self.banner.show_message(
                f"Imported: {result['added']} added,"
                f" {result['updated']} updated,"
                f" {result['skipped']} identical skipped.", 'success')
            self._hide_conflicts()
            return
        self.banner.show_message(
            f"{preview['additions']} addition(s),"
            f" {preview['identical']} identical,"
            f" {len(preview['conflicts'])} conflict(s)"
            ' -- resolve below.', 'info')
        self._show_conflicts(preview['conflicts'])

    def _show_conflicts(self, conflicts: list[dict]) -> None:
        self._conflicts = conflicts
        self.conflict_table.setRowCount(len(conflicts))
        self.conflict_groups = []
        for row, c in enumerate(conflicts):
            item = QTableWidgetItem(c['id'])
            item.setFlags(Qt.ItemIsEnabled)
            self.conflict_table.setItem(row, 0, item)

            group = QButtonGroup(self)
            mine = QRadioButton(self._short(c['local_value']))
            theirs = QRadioButton(self._short(c['incoming_value']))
            mine.setChecked(True)
            group.addButton(mine, 0)
            group.addButton(theirs, 1)
            self.conflict_table.setCellWidget(row, 1, mine)
            self.conflict_table.setCellWidget(row, 2, theirs)
            self.conflict_groups.append((c['id'], group))

            for col, ts in ((3, c['local_updated_at']),
                            (4, c['incoming_updated_at'])):
                item = QTableWidgetItem(format_timestamp(ts))
                item.setFlags(Qt.ItemIsEnabled)
                self.conflict_table.setItem(row, col, item)
        self.conflict_table.setVisible(True)
        self.bulk_row.setVisible(True)

    @staticmethod
    def _short(value: str, n: int = 24) -> str:
        value = str(value)
        return value if len(value) <= n else value[:n] + '…'

    def bulk_resolve(self, decision: int) -> None:
        for _, group in self.conflict_groups:
            group.button(decision).setChecked(True)

    def bulk_newer(self) -> None:
        by_id = {c['id']: c for c in self._conflicts}
        for cid, group in self.conflict_groups:
            c = by_id[cid]
            newer = ((c['incoming_updated_at'] or 0)
                     > (c['local_updated_at'] or 0))
            group.button(1 if newer else 0).setChecked(True)

    def do_apply(self) -> None:
        resolutions = {
            cid: ('theirs' if group.checkedId() == 1 else 'mine')
            for cid, group in self.conflict_groups
        }
        try:
            result = self.facade.import_apply(resolutions)
        except Exception as e:
            self.banner.show_message(str(e), 'error')
            return
        self.banner.show_message(
            f"Merged: {result['added']} added, {result['updated']}"
            f" updated, {result['kept']} kept,"
            f" {result['skipped']} identical skipped.", 'success')
        self._hide_conflicts()


def pretty_json(text: str) -> str:
    try:
        return json.dumps(json.loads(text), indent=2)
    except json.JSONDecodeError:
        return text
