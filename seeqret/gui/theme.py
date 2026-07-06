"""Dark QSS theme mirroring jseeqret's CSS custom properties.

   Palette source: jseeqret ``src/renderer/src/assets/main.css``.
"""

BG = '#1a1a2e'
BG_CARD = '#16213e'
BG_INPUT = '#0f3460'
BG_SIDEBAR = '#111827'
TEXT = '#e8eaf0'
TEXT_MUTED = '#a3adc2'
ACCENT = '#e94560'
ACCENT_HOVER = '#ff6b81'
SUCCESS = '#4ecca3'
WARNING = '#f5b04c'
DANGER = '#ff7d92'
BORDER = '#2a2a4a'
MONO = 'Consolas, Monaco, monospace'

STYLESHEET = f'''
QWidget {{
    background: {BG};
    color: {TEXT};
    font-size: 13px;
}}
QMainWindow {{ background: {BG}; }}

/* ---- sidebar --------------------------------------------------- */
QListWidget#sidebar {{
    background: {BG_SIDEBAR};
    border: none;
    outline: none;
    padding-top: 8px;
}}
QListWidget#sidebar::item {{
    padding: 10px 16px;
    border-left: 3px solid transparent;
    color: {TEXT_MUTED};
}}
QListWidget#sidebar::item:selected {{
    background: {BG};
    border-left: 3px solid {ACCENT};
    color: {TEXT};
}}
QListWidget#sidebar::item:hover {{ color: {TEXT}; }}

QLabel#brand {{
    background: {BG_SIDEBAR};
    color: {TEXT};
    font-size: 18px;
    font-weight: bold;
    padding: 16px;
}}
QLabel#sidebar_footer {{
    background: {BG_SIDEBAR};
    color: {TEXT_MUTED};
    padding: 12px 16px;
    font-size: 11px;
}}

/* ---- content --------------------------------------------------- */
QLabel#view_title {{ font-size: 20px; font-weight: bold; }}
QLabel[class="muted"] {{ color: {TEXT_MUTED}; }}
QLabel[class="mono"] {{ font-family: {MONO}; color: {SUCCESS}; }}
QLabel#fingerprint {{
    font-family: {MONO};
    font-size: 36px;
    color: {SUCCESS};
}}

QFrame[class="card"] {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QFrame[class="card"] QLabel {{
    background: transparent;
    border: none;
}}
QLabel[class="stat_number"] {{
    font-size: 32px;
    font-weight: bold;
    color: {ACCENT};
}}

/* ---- inputs / buttons ------------------------------------------ */
QLineEdit, QComboBox, QTextEdit, QPlainTextEdit {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 8px;
    color: {TEXT};
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox QAbstractItemView {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
}}

QPushButton {{
    background: {ACCENT};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {ACCENT_HOVER}; }}
QPushButton:disabled {{ background: {BORDER}; color: {TEXT_MUTED}; }}
QPushButton[class="secondary"] {{
    background: {BG_INPUT};
    color: {TEXT};
    border: 1px solid {BORDER};
}}
QPushButton[class="secondary"]:hover {{ border-color: {ACCENT}; }}

/* ---- tables ----------------------------------------------------- */
QTableView {{
    background: {BG_CARD};
    alternate-background-color: {BG};
    border: 1px solid {BORDER};
    border-radius: 8px;
    gridline-color: {BORDER};
    selection-background-color: {BG_INPUT};
    selection-color: {TEXT};
}}
QHeaderView::section {{
    background: {BG_SIDEBAR};
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 8px;
    font-weight: 600;
}}
QTableView QTableCornerButton::section {{ background: {BG_SIDEBAR}; }}

QScrollBar:vertical {{
    background: {BG};
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

/* ---- dialogs ----------------------------------------------------- */
QDialog {{ background: {BG_CARD}; }}
QMessageBox {{ background: {BG_CARD}; }}
'''
