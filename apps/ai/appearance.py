"""Native Qt colors, widget styles and scalable line icons for KERNOVA AI."""
from functools import lru_cache
from string import Template

from PySide6.QtGui import QColor, QFont, QIcon, QPalette, QPixmap


_COLORS = {
    "light": dict(
        canvas="#ffffff", sidebar="#fafbfc", surface="#ffffff", inset="#f5f7fa",
        text="#101218", muted="#414751", hint="#6a707a", disabled="#8590a1",
        line="#dce2ea", softline="#e6eaf0", strongline="#becada", hover="#edf1f7",
        accent="#0755ff", blue="#0755ff", bluehover="#0548dc", selected="#e8effe",
        disabledblue="#4a77d9", danger="#b53c4d", pulse="#218f78", folder="#ae7d1b",
    ),
    "dark": dict(
        canvas="#0c0e12", sidebar="#101217", surface="#171a20", inset="#191d25",
        text="#edf1f8", muted="#bdc5d4", hint="#9aa6b9", disabled="#778395",
        line="#363d49", softline="#292f39", strongline="#526073", hover="#252c37",
        accent="#77a1ff", blue="#1766ff", bluehover="#347aff", selected="#202e49",
        disabledblue="#345fae", danger="#ff9ba7", pulse="#75d6b4", folder="#eac478",
    ),
}


_STYLE = Template("""
QWidget#appRoot, QWidget#mainPane, QDialog, QMessageBox { background: $canvas; color: $text; }
QWidget#sidebar { background: $sidebar; border-right: 1px solid $line; }
QWidget#topBar { background: $canvas; border-bottom: 1px solid $line; }
QWidget#sideFooter { background: $sidebar; border-top: 1px solid $line; }
QLabel { background: transparent; color: $text; }
QLabel#brandTitle { font-size: 24px; font-weight: 700; }
QLabel#heroTitle { font-size: 44px; font-weight: 700; padding: 0; }
QLabel#inlineStatus { color: $hint; font-size: 12px; }

QPushButton, QToolButton {
    background: $surface; color: $text; border: 1px solid $line;
    border-radius: 6px; padding: 5px 10px; min-height: 20px;
}
QPushButton:hover, QToolButton:hover { background: $hover; border-color: $strongline; }
QPushButton:pressed, QToolButton:pressed { background: $selected; border-color: $accent; }
QPushButton:focus, QToolButton:focus { border-color: $accent; }
QPushButton:disabled, QToolButton:disabled { background: $inset; border-color: $softline; color: $disabled; }

QPushButton#newChat, QPushButton#sendButton, QPushButton#onboardingButton {
    background: $blue; color: white; border: 1px solid $blue; font-weight: 600;
}
QPushButton#newChat {
    text-align: center; font-size: 20px; border-radius: 10px; min-height: 29px; padding: 8px 12px;
}
QPushButton#sendButton, QToolButton#sendButton {
    background: $blue; color: white; border: 1px solid $blue; border-radius: 9px;
}
QPushButton#newChat:hover, QPushButton#sendButton:hover, QToolButton#sendButton:hover,
QPushButton#onboardingButton:hover { background: $bluehover; border-color: $bluehover; }
QPushButton#newChat:focus, QPushButton#sendButton:focus, QPushButton#onboardingButton:focus,
QToolButton#sendButton:focus { border: 1px solid $text; }
QPushButton#sendButton:disabled, QToolButton#sendButton:disabled {
    background: $disabledblue; border-color: $disabledblue; color: white;
}
QPushButton#stopButton, QToolButton#stopButton { background: $surface; color: $muted; border-color: $line; }
QPushButton#stopButton:hover, QToolButton#stopButton:hover { color: $danger; border-color: $danger; }
QPushButton#stopButton:disabled, QToolButton#stopButton:disabled { color: $disabled; border-color: $softline; }

QListWidget, QTextBrowser, QPlainTextEdit, QLineEdit {
    background: $surface; color: $text; border: 1px solid $line;
    border-radius: 6px; selection-background-color: $blue; selection-color: white;
}
QListWidget::item:selected { background: $selected; color: $accent; }
QListWidget#historyList {
    background: $sidebar; border: none; border-radius: 0; outline: 0; font-size: 16px;
}
QListWidget#historyList::item {
    background: transparent; color: $muted; border: 1px solid transparent;
    border-radius: 5px; padding: 5px 8px; min-height: 17px; margin: 1px 0;
}
QListWidget#historyList::item:hover { background: $hover; color: $text; }
QListWidget#historyList::item:selected { background: $selected; color: $accent; }
QListWidget#historyList::item:selected:focus { border-color: $accent; }
QPushButton#sideAction, QToolButton#sideAction, QPushButton#historyDelete, QToolButton#historyDelete {
    background: transparent; color: $text; border: 1px solid transparent;
    text-align: left; font-size: 18px; padding: 4px 8px; min-height: 32px;
}
QPushButton#sideAction:hover, QToolButton#sideAction:hover,
QPushButton#historyDelete:hover, QToolButton#historyDelete:hover { background: $hover; color: $text; }
QPushButton#sideAction:focus, QToolButton#sideAction:focus,
QPushButton#historyDelete:focus, QToolButton#historyDelete:focus { border-color: $accent; }
QPushButton#historyDelete:disabled, QToolButton#historyDelete:disabled { color: $disabled; }

QPushButton#modeTab, QToolButton#modeTab {
    background: transparent; color: $muted; border: none;
    border-bottom: 3px solid transparent; border-radius: 0; font-size: 19px;
    padding: 0 18px; min-height: 60px;
}
QPushButton#modeTab:hover, QToolButton#modeTab:hover { color: $text; background: $inset; }
QPushButton#modeTab:checked, QToolButton#modeTab:checked {
    color: $accent; font-weight: 600; border-bottom: 3px solid $accent;
}
QPushButton#modeTab:focus, QToolButton#modeTab:focus { background: $selected; }
QPushButton#modeTab:disabled, QToolButton#modeTab:disabled { color: $disabled; }

QComboBox {
    background: $surface; color: $text; border: 1px solid $line;
    border-radius: 5px; min-height: 21px; padding: 3px 21px 3px 9px;
}
QComboBox::drop-down { subcontrol-position: right center; width: 19px; border: none; }
QComboBox#modelSelect { font-size: 18px; min-height: 30px; padding: 3px 24px 3px 10px; border-radius: 7px; }
QComboBox:focus, QComboBox:hover { border-color: $strongline; }
QComboBox:disabled { color: $disabled; }
QComboBox QAbstractItemView {
    background: $surface; color: $text; border: 1px solid $line;
    selection-background-color: $selected; selection-color: $accent;
}
QCheckBox { color: $muted; spacing: 6px; }
QCheckBox:disabled { color: $disabled; }

QTextBrowser#transcript { background: $canvas; font-size: 16px; border: none; border-radius: 0; padding: 0; }
QWidget#composer { background: $surface; border: 1px solid $strongline; border-radius: 13px; }
QPlainTextEdit#promptEdit { background: transparent; font-size: 20px; border: none; padding: 4px 1px 2px; }
QPushButton#quickAction, QToolButton#quickAction {
    color: $text; font-size: 19px; padding: 0 12px; min-height: 43px; border-radius: 11px;
}
QWidget#toolStrip { background: $canvas; }
QProgressBar {
    color: $text; background: $inset; border: 1px solid $line; border-radius: 4px;
    text-align: center; min-height: 14px;
}
QProgressBar::chunk { background: $blue; border-radius: 3px; }
QScrollBar:vertical { background: transparent; width: 9px; margin: 1px; }
QScrollBar::handle:vertical { background: $strongline; border-radius: 3px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QToolTip { background: $surface; color: $text; border: 1px solid $strongline; padding: 4px 7px; }
""")


def apply_theme(widget, theme):
    colors = _COLORS[theme]
    role = QPalette.ColorRole
    palette = QPalette(widget.palette())
    for color_role, token in (
        (role.Window, "canvas"), (role.WindowText, "text"), (role.Base, "surface"),
        (role.AlternateBase, "inset"), (role.Text, "text"), (role.Button, "surface"),
        (role.ButtonText, "text"), (role.PlaceholderText, "hint"), (role.Highlight, "blue"),
        (role.Link, "accent"), (role.LinkVisited, "accent"), (role.ToolTipBase, "surface"),
        (role.ToolTipText, "text"), (role.Mid, "line"), (role.Dark, "strongline"),
    ):
        palette.setColor(color_role, QColor(colors[token]))
    palette.setColor(role.HighlightedText, QColor("white"))
    for color_role in (role.Text, role.WindowText, role.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, color_role, QColor(colors["disabled"]))
    widget.setPalette(palette)
    font = QFont(widget.font())
    font.setFamilies(["Inter", "Noto Sans", "Segoe UI", "DejaVu Sans", "sans-serif"])
    font.setPixelSize(13)
    widget.setFont(font)
    widget.setStyleSheet(_STYLE.substitute(colors))


# Paths share a 24-unit grid, rounded joins and a consistent stroke width.
_PATHS = {
    "chat": "M21 11.6a8.9 8.4 0 0 1-9 8.4 10 10 0 0 1-3.8-.7l-4.6 1.4 1.2-4.2A8.1 8.1 0 0 1 3 11.6a9 8.4 0 0 1 18 0Z",
    "support": "M4 15v-3a8 8 0 0 1 16 0v3 M6.5 12H5a2 2 0 0 0-2 2v2a2 2 0 0 0 2 2h1.5z M17.5 12H19a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2h-1.5z M19 18a3.5 3.5 0 0 1-3.5 3.5H13",
    "code": "m8 6-6 6 6 6 m8-12 6 6-6 6 m-3-15-3 18",
    "plus": "M12 5v14 M5 12h14",
    "models": "M7.5 5h9a2.5 2.5 0 0 1 2.5 2.5v9a2.5 2.5 0 0 1-2.5 2.5h-9A2.5 2.5 0 0 1 5 16.5v-9A2.5 2.5 0 0 1 7.5 5Z M9 9h6v6H9Z M9 2v3 M15 2v3 M9 19v3 M15 19v3 M2 9h3 M2 15h3 M19 9h3 M19 15h3",
    "settings": "m10.2 3 .4-1h2.8l.5 1.8 1.7.8 1.8-.6 2 2-1 1.8.7 1.7 1.9.5v3l-1.9.6-.7 1.6.9 1.8-2 2-1.8-.8-1.7.7-.5 1.9h-2.9l-.5-1.9-1.7-.7-1.8.8-2-2 .9-1.8-.7-1.7-1.9-.5v-3l1.9-.5.7-1.7-.9-1.8 2-2 1.8.7 1.7-.7z M15.2 12a3.2 3.2 0 1 1-6.4 0 3.2 3.2 0 0 1 6.4 0Z",
    "send": "M12 20V4 M4.5 11.5 12 4l7.5 7.5",
    "stop": "M6.2 5.5h11.6a.7.7 0 0 1 .7.7v11.6a.7.7 0 0 1-.7.7H6.2a.7.7 0 0 1-.7-.7V6.2a.7.7 0 0 1 .7-.7Z",
    "pulse": "M2 12h4.5L10 4l4.2 16 3.1-8H22",
    "folder": "M2.5 6a1.5 1.5 0 0 1 1.5-1.5h5l2 2h9A1.5 1.5 0 0 1 21.5 8v10a1.5 1.5 0 0 1-1.5 1.5H4A1.5 1.5 0 0 1 2.5 18Z",
    "trash": "M4.5 6.5h15 M9 6V4.5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1V6 M6.5 7l.8 12.5a1.5 1.5 0 0 0 1.5 1.4h6.4a1.5 1.5 0 0 0 1.5-1.4L17.5 7 M10 10v7 M14 10v7",
    "history": "M3.2 10A9 9 0 1 1 4 16 M3.2 5v5h5 M12 7v5l3.6 2.3",
    "chevron": "m6.5 9.2 5.5 5.5 5.5-5.5",
    "sun": "M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z M12 2v2 M12 20v2 M2 12h2 M20 12h2 M5 5l1.5 1.5 M17.5 17.5 19 19 M19 5l-1.5 1.5 M6.5 17.5 5 19",
    "moon": "M20.2 14.7A8.9 8.9 0 0 1 9.3 3.8a8.8 8.8 0 1 0 10.9 10.9Z",
}


@lru_cache(maxsize=96)
def icon(name, theme, active=False):
    """Render an icon in the current palette, with sharp pixmaps for common display scales."""
    colors = _COLORS[theme]
    ink = colors["accent" if active else "muted"]
    if name in ("send", "plus"):
        ink = "#ffffff"
    elif name in ("pulse", "folder"):
        ink = colors[name]
    result = QIcon()
    disabled_ink = "#eff5ff" if name == "send" else colors["disabled"]
    for mode, color in ((QIcon.Mode.Normal, ink), (QIcon.Mode.Disabled, disabled_ink)):
        for size in (16, 20, 24, 32, 48, 64):
            svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24">'
                   f'<path d="{_PATHS[name]}" fill="none" stroke="{color}" stroke-width="1.65" '
                   'stroke-linecap="round" stroke-linejoin="round"/></svg>')
            pixmap = QPixmap()
            pixmap.loadFromData(svg.encode("ascii"), "SVG")
            result.addPixmap(pixmap, mode)
    return result
