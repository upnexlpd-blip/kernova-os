"""Native Qt colors, compact IDE styles and scalable line icons for KERNOVA AI."""
from functools import lru_cache
from string import Template

from PySide6.QtGui import QColor, QFont, QIcon, QPalette, QPixmap


_COLORS = {
    "light": dict(
        canvas="#ffffff", sidebar="#f6f7f9", workspace="#f9fafc", surface="#ffffff", inset="#f0f3f8",
        composer="#f8f9fc", menu="#ffffff",
        text="#11141a", muted="#4a515d", hint="#6e7684", disabled="#909aa8",
        line="#dfe4ec", softline="#eaeef4", strongline="#c5cedb", hover="#eceff5",
        accent="#145eff", blue="#1a66ff", bluehover="#0f53de", selected="#e8f0fe",
        disabledblue="#6e95e6", danger="#c23b4d", pulse="#1b8a72", folder="#a87615",
    ),
    "dark": dict(
        canvas="#0b0d10", sidebar="#0e1015", workspace="#0d0f14", surface="#14171f", inset="#191d27",
        composer="#12151c", menu="#161922",
        text="#e8ecf4", muted="#a8b2c3", hint="#7c8799", disabled="#596375",
        line="#232834", softline="#1b202a", strongline="#323a4b", hover="#1a1f2a",
        accent="#70a2ff", blue="#256bff", bluehover="#3c7cff", selected="#1b263b",
        disabledblue="#25427a", danger="#ff8f9c", pulse="#66d4b0", folder="#e4be70",
    ),
}

_SCALES = {"compact": 0, "normal": 1, "large": 2}


_STYLE = Template("""
QWidget#appRoot, QWidget#mainPane, QDialog, QMessageBox { background: $canvas; color: $text; font-size: ${base}px; }
QWidget#sidebar { background: $sidebar; border-right: 1px solid $line; }
QWidget#workspacePane { background: $workspace; border-left: 1px solid $line; }
QWidget#topBar { background: $canvas; border-bottom: 1px solid $line; }
QWidget#menuStrip { background: $sidebar; border-bottom: 1px solid $softline; }
QWidget#sideFooter { background: $sidebar; border-top: 1px solid $softline; }
QLabel { background: transparent; color: $text; font-size: ${base}px; }
QLabel#brandTitle { font-size: ${brand}px; font-weight: 600; color: $text; }
QLabel#sectionTitle { font-size: ${small}px; font-weight: 600; color: $hint; padding: 2px 4px; }
QLabel#heroTitle { font-size: ${hero}px; font-weight: 600; padding: 0; color: $text; }
QLabel#inlineStatus { color: $hint; font-size: ${small}px; }
QLabel#paneTitle { font-size: ${base}px; font-weight: 600; color: $text; }

QPushButton, QToolButton {
    background: $surface; color: $text; border: 1px solid $line;
    border-radius: 6px; padding: 4px 9px; min-height: 20px; font-size: ${base}px;
}
QPushButton:hover, QToolButton:hover { background: $hover; border-color: $strongline; }
QPushButton:pressed, QToolButton:pressed { background: $selected; border-color: $accent; }
QPushButton:focus, QToolButton:focus { border-color: $accent; }
QPushButton:disabled, QToolButton:disabled { background: $inset; border-color: $softline; color: $disabled; }

QPushButton#menuButton, QToolButton#menuButton {
    background: transparent; color: $muted; border: 1px solid transparent;
    border-radius: 4px; padding: 2px 7px; min-height: 20px; font-size: ${small}px;
}
QPushButton#menuButton:hover, QToolButton#menuButton:hover { background: $hover; color: $text; }
QToolButton#menuButton::menu-indicator { image: none; width: 0; }

QPushButton#iconNav, QToolButton#iconNav {
    background: transparent; color: $muted; border: 1px solid transparent;
    border-radius: 5px; padding: 2px; min-height: 22px; min-width: 22px;
}
QPushButton#iconNav:hover, QToolButton#iconNav:hover { background: $hover; color: $text; }
QPushButton#iconNav:disabled, QToolButton#iconNav:disabled { background: transparent; color: $disabled; }
QToolButton#iconNav::menu-indicator { image: none; width: 0; }

QPushButton#newChat {
    background: $surface; color: $text; border: 1px solid $line;
    text-align: left; font-size: ${plus1}px; font-weight: 600;
    border-radius: 7px; min-height: 24px; padding: 5px 10px;
}
QPushButton#newChat:hover { background: $hover; border-color: $strongline; }

QPushButton#onboardingButton {
    background: $blue; color: white; border: 1px solid $blue; font-weight: 600; border-radius: 6px;
}
QPushButton#onboardingButton:hover { background: $bluehover; border-color: $bluehover; }

QPushButton#sendButton, QToolButton#sendButton {
    background: $blue; color: white; border: 1px solid $blue; border-radius: 14px; padding: 0; min-height: 28px; min-width: 28px;
}
QPushButton#sendButton:hover, QToolButton#sendButton:hover { background: $bluehover; border-color: $bluehover; }
QPushButton#sendButton:disabled, QToolButton#sendButton:disabled {
    background: $disabledblue; border-color: $disabledblue; color: white;
}
QPushButton#stopButton, QToolButton#stopButton {
    background: $surface; color: $muted; border: 1px solid $strongline; border-radius: 14px; padding: 0; min-height: 28px; min-width: 28px;
}
QPushButton#stopButton:hover, QToolButton#stopButton:hover { color: $danger; border-color: $danger; }

QPushButton#composerPlus, QToolButton#composerPlus {
    background: transparent; color: $muted; border: 1px solid transparent;
    border-radius: 6px; padding: 2px 6px; min-height: 22px; font-size: ${plus1}px;
}
QPushButton#composerPlus:hover, QToolButton#composerPlus:hover { background: $hover; color: $text; }
QToolButton#composerPlus::menu-indicator { image: none; width: 0; }

QPushButton#intentButton, QToolButton#intentButton {
    background: transparent; color: $muted; border: 1px solid transparent;
    border-radius: 6px; padding: 2px 8px; min-height: 22px; font-size: ${small}px;
}
QPushButton#intentButton:hover, QToolButton#intentButton:hover { background: $hover; color: $text; }
QToolButton#intentButton::menu-indicator { image: none; width: 0; }

QPushButton#chipButton {
    background: $inset; color: $muted; border: 1px solid $line;
    border-radius: 11px; padding: 2px 9px; min-height: 18px; font-size: ${small}px;
}
QPushButton#chipButton:hover { background: $hover; color: $text; border-color: $strongline; }
QPushButton#chipButton:checked { background: $selected; color: $accent; border-color: $accent; }

QListWidget, QTextBrowser, QPlainTextEdit, QLineEdit {
    background: $surface; color: $text; border: 1px solid $line;
    border-radius: 6px; selection-background-color: $blue; selection-color: white;
    font-size: ${base}px;
}
QLineEdit { padding: 4px 8px; min-height: 20px; }
QLineEdit#pillSearch {
    background: $surface; border: 1px solid $line; border-radius: 14px;
    padding: 4px 12px; min-height: 22px; font-size: ${small}px;
}
QLineEdit#pillSearch:focus { border: 1px solid $blue; }
QLineEdit#sideSearch {
    background: $surface; border: 1px solid $line; border-radius: 6px;
    padding: 3px 8px; min-height: 20px; font-size: ${small}px;
}
QLineEdit#sideSearch:focus { border: 1px solid $accent; }

QListWidget::item:selected { background: $selected; color: $accent; }
QListWidget#historyList, QListWidget#projectList {
    background: transparent; border: none; border-radius: 0; outline: 0; font-size: ${base}px;
}
QListWidget#historyList::item, QListWidget#projectList::item {
    background: transparent; color: $muted; border: 1px solid transparent;
    border-radius: 7px; padding: 0px; min-height: 28px; margin: 1px 0;
}
QListWidget#historyList::item:hover, QListWidget#projectList::item:hover { background: $hover; color: $text; }
QListWidget#historyList::item:selected, QListWidget#projectList::item:selected {
    background: $surface; color: $text; border: 1px solid $strongline; font-weight: 600;
}
QPushButton#rowAction, QToolButton#rowAction {
    background: transparent; color: $muted; border: none;
    border-radius: 10px; padding: 0px; min-height: 20px; min-width: 20px; max-height: 20px; max-width: 20px;
}
QPushButton#rowAction:hover, QToolButton#rowAction:hover { background: $strongline; color: $text; }
QToolButton#rowAction::menu-indicator { image: none; width: 0; }
QLabel#rowAge { color: $hint; font-size: ${small}px; background: transparent; }
QLabel#unreadDot { color: $accent; font-size: ${plus1}px; font-weight: 700; background: transparent; }

QPushButton#sideAction, QToolButton#sideAction, QPushButton#historyDelete, QToolButton#historyDelete {
    background: transparent; color: $muted; border: 1px solid transparent;
    text-align: left; font-size: ${base}px; padding: 4px 7px; min-height: 24px; border-radius: 6px;
}
QPushButton#sideAction:hover, QToolButton#sideAction:hover,
QPushButton#historyDelete:hover, QToolButton#historyDelete:hover { background: $hover; color: $text; }

QPushButton#workspaceItem {
    background: transparent; color: $muted; border: 1px solid transparent;
    text-align: left; font-size: ${base}px; padding: 5px 10px; min-height: 24px; border-radius: 6px;
}
QPushButton#workspaceItem:hover { background: $hover; color: $text; }

QPushButton#modeTab, QToolButton#modeTab {
    background: transparent; color: $muted; border: none;
    border-bottom: 2px solid transparent; border-radius: 0; font-size: ${base}px;
    padding: 0 10px; min-height: 34px;
}
QPushButton#modeTab:hover, QToolButton#modeTab:hover { color: $text; background: $inset; }
QPushButton#modeTab:checked, QToolButton#modeTab:checked {
    color: $accent; font-weight: 600; border-bottom: 2px solid $accent;
}

QComboBox {
    background: $surface; color: $text; border: 1px solid $line;
    border-radius: 5px; min-height: 20px; padding: 2px 20px 2px 8px; font-size: ${small}px;
}
QComboBox::drop-down { subcontrol-position: right center; width: 18px; border: none; }
QComboBox#modelSelect {
    background: transparent; color: $muted; border: 1px solid transparent;
    font-size: ${small}px; min-height: 22px; padding: 2px 22px 2px 6px; border-radius: 6px;
}
QComboBox#modelSelect:hover, QComboBox#modelSelect:focus { background: $hover; color: $text; }
QComboBox QAbstractItemView {
    background: $menu; color: $text; border: 1px solid $strongline;
    selection-background-color: $selected; selection-color: $accent;
    font-size: ${small}px;
}

QMenu {
    background: $menu; color: $text; border: 1px solid $strongline;
    border-radius: 8px; padding: 5px; font-size: ${base}px;
}
QMenu::item { padding: 5px 22px 5px 10px; border-radius: 5px; }
QMenu::item:selected { background: $hover; color: $text; }
QMenu::item:disabled { color: $disabled; }
QMenu::separator { height: 1px; background: $softline; margin: 4px 6px; }

QCheckBox { color: $muted; spacing: 5px; font-size: ${small}px; }
QCheckBox:disabled { color: $disabled; }

QTextBrowser#transcript { background: $canvas; font-size: ${plus1}px; border: none; border-radius: 0; padding: 0; }
QWidget#composer { background: $composer; border: 1px solid $line; border-radius: 12px; }
QFrame#composerDivider { background: $softline; border: none; max-height: 1px; min-height: 1px; }
QPlainTextEdit#promptEdit {
    background: transparent; font-size: ${plus1}px; border: none; padding: 4px 2px 2px;
}
QPlainTextEdit#terminalView, QPlainTextEdit#codePreview {
    background: $sidebar; color: $text; border: 1px solid $line; border-radius: 6px;
    font-size: ${small}px; padding: 6px;
}

QPushButton#quickAction, QToolButton#quickAction {
    background: $surface; color: $muted; border: 1px solid $line;
    font-size: ${small}px; padding: 0 11px; min-height: 28px; border-radius: 14px;
}
QPushButton#quickAction:hover, QToolButton#quickAction:hover {
    background: $hover; color: $text; border-color: $strongline;
}

QWidget#toolStrip { background: $canvas; border-bottom: 1px solid $softline; }
QProgressBar {
    color: $text; background: $inset; border: 1px solid $line; border-radius: 4px;
    text-align: center; min-height: 12px; font-size: ${small}px;
}
QProgressBar::chunk { background: $blue; border-radius: 3px; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 1px; }
QScrollBar::handle:vertical { background: $strongline; border-radius: 3px; min-height: 22px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QToolTip { background: $menu; color: $text; border: 1px solid $strongline; padding: 4px 7px; font-size: ${small}px; }
""")


def colors_for(theme):
    return _COLORS["dark" if theme == "dark" else "light"]


def apply_theme(widget, theme, scale="compact"):
    colors = colors_for(theme)
    step = _SCALES.get(scale, 0)
    sizes = dict(
        small=11 + step,
        base=12 + step,
        plus1=13 + step,
        brand=14 + step,
        hero=22 + step * 2,
    )
    role = QPalette.ColorRole
    palette = QPalette(widget.palette())
    for color_role, token in (
        (role.Window, "canvas"), (role.WindowText, "text"), (role.Base, "surface"),
        (role.AlternateBase, "inset"), (role.Text, "text"), (role.Button, "surface"),
        (role.ButtonText, "text"), (role.PlaceholderText, "hint"), (role.Highlight, "blue"),
        (role.Link, "accent"), (role.LinkVisited, "accent"), (role.ToolTipBase, "menu"),
        (role.ToolTipText, "text"), (role.Mid, "line"), (role.Dark, "strongline"),
    ):
        palette.setColor(color_role, QColor(colors[token]))
    palette.setColor(role.HighlightedText, QColor("white"))
    for color_role in (role.Text, role.WindowText, role.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, color_role, QColor(colors["disabled"]))
    widget.setPalette(palette)
    font = QFont(widget.font())
    font.setFamilies(["Inter", "Segoe UI", "Noto Sans", "DejaVu Sans", "sans-serif"])
    font.setPixelSize(sizes["base"])
    widget.setFont(font)
    widget.setStyleSheet(_STYLE.substitute({**colors, **sizes}))


# Paths share a 24-unit grid, rounded joins and a consistent stroke width.
_PATHS = {
    "chat": "M21 11.6a8.9 8.4 0 0 1-9 8.4 10 10 0 0 1-3.8-.7l-4.6 1.4 1.2-4.2A8.1 8.1 0 0 1 3 11.6a9 8.4 0 0 1 18 0Z",
    "support": "M4 15v-3a8 8 0 0 1 16 0v3 M6.5 12H5a2 2 0 0 0-2 2v2a2 2 0 0 0 2 2h1.5z M17.5 12H19a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2h-1.5z M19 18a3.5 3.5 0 0 1-3.5 3.5H13",
    "code": "m8 6-6 6 6 6 m8-12 6 6-6 6 m-3-15-3 18",
    "plus": "M12 5v14 M5 12h14",
    "models": "M7.5 5h9a2.5 2.5 0 0 1 2.5 2.5v9a2.5 2.5 0 0 1-2.5 2.5h-9A2.5 2.5 0 0 1 5 16.5v-9A2.5 2.5 0 0 1 7.5 5Z M9 9h6v6H9Z M9 2v3 M15 2v3 M9 19v3 M15 19v3 M2 9h3 M2 15h3 M19 9h3 M19 15h3",
    "settings": "m10.2 3 .4-1h2.8l.5 1.8 1.7.8 1.8-.6 2 2-1 1.8.7 1.7 1.9.5v3l-1.9.6-.7 1.6.9 1.8-2 2-1.8-.8-1.7.7-.5 1.9h-2.9l-.5-1.9-1.7-.7-1.8.8-2-2 .9-1.8-.7-1.7-1.9-.5v-3l1.9-.5.7-1.7-.9-1.8 2-2 1.8.7 1.7-.7z M15.2 12a3.2 3.2 0 1 1-6.4 0 3.2 3.2 0 0 1 6.4 0Z",
    "send": "M4.5 12h15 M13 5.5 19.5 12 13 18.5",
    "stop": "M7 7h10v10H7Z",
    "pulse": "M2 12h4.5L10 4l4.2 16 3.1-8H22",
    "folder": "M2.5 6a1.5 1.5 0 0 1 1.5-1.5h5l2 2h9A1.5 1.5 0 0 1 21.5 8v10a1.5 1.5 0 0 1-1.5 1.5H4A1.5 1.5 0 0 1 2.5 18Z",
    "folder_plus": "M2.5 6a1.5 1.5 0 0 1 1.5-1.5h5l2 2h9A1.5 1.5 0 0 1 21.5 8v10a1.5 1.5 0 0 1-1.5 1.5H4A1.5 1.5 0 0 1 2.5 18Z M12 10.5v5 M9.5 13h5",
    "trash": "M4.5 6.5h15 M9 6V4.5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1V6 M6.5 7l.8 12.5a1.5 1.5 0 0 0 1.5 1.4h6.4a1.5 1.5 0 0 0 1.5-1.4L17.5 7 M10 10v7 M14 10v7",
    "history": "M3.2 10A9 9 0 1 1 4 16 M3.2 5v5h5 M12 7v5l3.6 2.3",
    "clock": "M12 3a9 9 0 1 0 9 9 9 9 0 0 0-9-9Z M12 7.5V12l3.2 2",
    "briefcase": "M4 8h16a1.5 1.5 0 0 1 1.5 1.5v8A1.5 1.5 0 0 1 20 19H4a1.5 1.5 0 0 1-1.5-1.5v-8A1.5 1.5 0 0 1 4 8Z M9 8V6a1.5 1.5 0 0 1 1.5-1.5h3A1.5 1.5 0 0 1 15 6v2 M2.5 12.5h19",
    "sidebar_left": "M4 5h16a1.5 1.5 0 0 1 1.5 1.5v11A1.5 1.5 0 0 1 20 19H4a1.5 1.5 0 0 1-1.5-1.5v-11A1.5 1.5 0 0 1 4 5Z M9 5v14",
    "sidebar_right": "M4 5h16a1.5 1.5 0 0 1 1.5 1.5v11A1.5 1.5 0 0 1 20 19H4a1.5 1.5 0 0 1-1.5-1.5v-11A1.5 1.5 0 0 1 4 5Z M15 5v14",
    "arrow_left": "M19 12H5 M11 6l-6 6 6 6",
    "arrow_right": "M5 12h14 M13 6l6 6-6 6",
    "search": "M11 4a7 7 0 1 0 4.95 11.95L20 20",
    "filter": "M4 7h16 M7 12h10 M10 17h4",
    "review": "M6 3.5h8.5L19 8v12.5H6Z M14.5 3.5V8H19 M9 12h6 M9 15.5h6",
    "file": "M6 3.5h8.5L19 8v12.5H6Z M14.5 3.5V8H19",
    "terminal": "M4 5h16a1.5 1.5 0 0 1 1.5 1.5v11A1.5 1.5 0 0 1 20 19H4a1.5 1.5 0 0 1-1.5-1.5v-11A1.5 1.5 0 0 1 4 5Z m3 4.5 3 2.5-3 2.5 m5 0h4",
    "globe": "M12 3a9 9 0 1 0 9 9 9 9 0 0 0-9-9Z M3.5 12h17 M12 3a13.5 13.5 0 0 1 0 18 M12 3a13.5 13.5 0 0 0 0 18",
    "side_chat": "M4 5.5h16v10H8l-4 3.5Z M9 10.5h6 M12 8v5",
    "plugin": "M9 4.5a2 2 0 0 1 4 0V6h3.5A1.5 1.5 0 0 1 18 7.5V11h1.5a2 2 0 0 1 0 4H18v3.5a1.5 1.5 0 0 1-1.5 1.5H13v-1.5a2 2 0 0 0-4 0V20H5.5A1.5 1.5 0 0 1 4 18.5V15h1.5a2 2 0 0 0 0-4H4V7.5A1.5 1.5 0 0 1 5.5 6H9Z",
    "paperclip": "m15.5 7.5-6.8 6.8a2.2 2.2 0 0 0 3.1 3.1l7.4-7.4a4.2 4.2 0 0 0-6-6L5.8 11.4a6.2 6.2 0 0 0 8.8 8.8l5.9-5.9",
    "at": "M16 12a4 4 0 1 1-4-4 4 4 0 0 1 4 4v1.5a2.2 2.2 0 0 0 4.4 0V12a8.4 8.4 0 1 0-4.6 7.5",
    "bolt": "M13 2.5 5.5 13h5.5l-1 8.5L18.5 11H13Z",
    "shield": "M12 3 5 6v5.5C5 16.5 8 20 12 21.5c4-1.5 7-5 7-10V6Z",
    "plan": "M5 6h14 M5 12h14 M5 18h9 M17 16l2 2 3-3.5",
    "beaker": "M9 3h6 M10 3v5.5L5.2 18a1.8 1.8 0 0 0 1.6 2.6h10.4A1.8 1.8 0 0 0 18.8 18L14 8.5V3 M7.5 14.5h9",
    "bulb": "M9 18h6 M10 21h4 M12 3a6 6 0 0 0-3.6 10.8c.7.6 1.1 1.4 1.1 2.2h5c0-.8.4-1.6 1.1-2.2A6 6 0 0 0 12 3Z",
    "expand": "M4 9V4h5 M20 9V4h-5 M4 15v5h5 M20 15v5h-5",
    "more": "M12 5.5v.2 M12 11.9v.2 M12 18.3v.2",
    "edit_pen": "M15.8 4.2a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z",
    "pin": "M9 4h6l-1 5 3 3v2H7v-2l3-3-1-5Z M12 14v6",
    "unread": "M19 9.5V16a2 2 0 0 1-2 2H8l-4 3V6a2 2 0 0 1 2-2h7.5 M18.5 5.5a2 2 0 1 0 0 .1Z",
    "copy_doc": "M9 9h9a1.5 1.5 0 0 1 1.5 1.5v9A1.5 1.5 0 0 1 18 21H9a1.5 1.5 0 0 1-1.5-1.5v-9A1.5 1.5 0 0 1 9 9Z M5 15H4.5A1.5 1.5 0 0 1 3 13.5v-9A1.5 1.5 0 0 1 4.5 3h9A1.5 1.5 0 0 1 15 4.5V5",
    "split": "M4 5h6v14H4Z M14 5h6v10h-6Z M17 18v4 M15 20h4",
    "archive": "M4 5h16v3.5H4Z M5.5 8.5v10A1.5 1.5 0 0 0 7 20h10a1.5 1.5 0 0 0 1.5-1.5v-10 M12 11.5v5 M9.5 14l2.5 2.5 2.5-2.5",
    "chevron": "m7 9.5 5 5 5-5",
    "chevron_right": "m9.5 7 5 5-5 5",
    "sun": "M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z M12 2v2 M12 20v2 M2 12h2 M20 12h2 M5 5l1.5 1.5 M17.5 17.5 19 19 M19 5l-1.5 1.5 M6.5 17.5 5 19",
    "moon": "M20.2 14.7A8.9 8.9 0 0 1 9.3 3.8a8.8 8.8 0 1 0 10.9 10.9Z",
}


@lru_cache(maxsize=160)
def icon(name, theme, active=False):
    """Render an icon in the current palette, with sharp pixmaps for common display scales."""
    colors = colors_for(theme)
    ink = colors["accent" if active else "muted"]
    if name == "send":
        ink = "#ffffff"
    elif name == "pulse":
        ink = colors[name]
    result = QIcon()
    disabled_ink = "#eff5ff" if name == "send" else colors["disabled"]
    for mode, color in ((QIcon.Mode.Normal, ink), (QIcon.Mode.Disabled, disabled_ink)):
        for size in (16, 32):
            svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24">'
                   f'<path d="{_PATHS[name]}" fill="none" stroke="{color}" stroke-width="1.75" '
                   'stroke-linecap="round" stroke-linejoin="round"/></svg>')
            pixmap = QPixmap()
            pixmap.loadFromData(svg.encode("ascii"), "SVG")
            result.addPixmap(pixmap, mode)
    return result
