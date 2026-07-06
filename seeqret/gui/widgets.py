"""Shared small widgets and formatters for the seeqret GUI.
"""
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .theme import ACCENT, DANGER, SUCCESS, TEXT_MUTED


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


def view_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName('view_title')
    return label


def make_card(title: str, body: str, big: bool = False) -> QFrame:
    card = QFrame()
    card.setProperty('class', 'card')
    layout = QVBoxLayout(card)
    body_label = QLabel(body)
    body_label.setProperty('class', 'stat_number' if big else 'mono')
    body_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    body_label.setWordWrap(True)
    title_label = QLabel(title)
    title_label.setProperty('class', 'muted')
    layout.addWidget(body_label)
    layout.addWidget(title_label)
    return card


class Banner(QLabel):
    """Inline alert label (jseeqret uses per-view banners, not toasts).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setVisible(False)

    def show_message(self, text: str, kind: str = 'info') -> None:
        color = {'error': DANGER, 'success': SUCCESS,
                 'info': TEXT_MUTED}.get(kind, TEXT_MUTED)
        self.setStyleSheet(
            f'color: {color}; border: 1px solid {color};'
            f' border-radius: 6px; padding: 8px;')
        self.setText(text)
        self.setVisible(True)

    def clear_message(self) -> None:
        self.setVisible(False)


class Segmented(QWidget):
    """A jseeqret-style segmented toggle (Clipboard/File/Slack...).
    """

    def __init__(self, options: list[str], parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        for i, option in enumerate(options):
            btn = QPushButton(option)
            btn.setCheckable(True)
            btn.setProperty('class', 'secondary')
            if i == 0:
                btn.setChecked(True)
            self.group.addButton(btn, i)
            layout.addWidget(btn)
        self.options = options

    @property
    def value(self) -> str:
        return self.options[self.group.checkedId()]


def fingerprint_label(fp: str) -> QLabel:
    label = QLabel(fp)
    label.setObjectName('fingerprint')
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return label


def status_dot(ok: bool) -> str:
    """Colored traffic-light dot as rich text.
    """
    color = SUCCESS if ok else ACCENT
    return f'<span style="color:{color}">●</span>'
