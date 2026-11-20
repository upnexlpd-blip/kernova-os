"""The English proposal shown inside KERNOVA Welcome."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QSizePolicy, QVBoxLayout


TITLE = "Kernova 2.0 Pro"
PRICE_NOTE = "Proposed price for one computer."
ROWS = (
    ("Feature", "Kernova OS", TITLE),
    ("Gaming", "Choose a profile manually", "Automatic profile for each game"),
    ("Projects", "Open your tools separately", "Open a whole project in one click"),
    ("Backups", "Manual backup guide", "Scheduled backups and restore by date"),
    ("Price", "Free", "€29 one-time"),
)

# Apply the proposal palette only while its page is open.
WINDOW_STYLE = """
    QWidget#kernovaWelcome, QScrollArea#proScroll, QWidget#proPage {
        background-color: #192231; color: #f1f4ff;
    }
    QWidget#kernovaWelcome QLabel, QWidget#kernovaWelcome QCheckBox { color: #f1f4ff; }
    QWidget#kernovaWelcome QListWidget {
        background: #141d2c; color: #f1f4ff; border: 1px solid #99acdf;
        border-radius: 5px; padding: 3px;
    }
    QWidget#kernovaWelcome QListWidget::item { padding: 5px 2px; }
    QWidget#kernovaWelcome QListWidget::item:selected { background: #afc1ff; color: #111b2b; }
    QWidget#kernovaWelcome QPushButton { background: #29374a; color: #f1f4ff;
        border: 1px solid #68778c; border-radius: 4px; padding: 5px 14px; }
    QWidget#kernovaWelcome QPushButton:focus { border-color: #b2c5ff; }
"""


def build_comparison(layout: QVBoxLayout):
    hero = QFrame()
    hero.setObjectName("proHero")
    artwork = Path(__file__).with_name("icons") / "pro-ribbon.jpg"
    hero.setStyleSheet(
        f'QFrame#proHero {{ background: #131d31; border-image: url("{artwork.as_posix()}") 0 stretch stretch; }}'
    )
    header = QVBoxLayout(hero)
    header.setContentsMargins(16, 24, 12, 19)
    header.setSpacing(4)
    badge = QLabel("Proposal")
    badge.setStyleSheet("background: #b6c6ff; color: #111b2b; border-radius: 9px; padding: 2px 9px; font-weight: bold;")
    header.addWidget(badge, alignment=Qt.AlignmentFlag.AlignLeft)
    title = QLabel(TITLE)
    title.setWordWrap(True)
    font = title.font()
    font.setBold(True)
    font.setPointSizeF(max(18, font.pointSizeF() * 2.2))
    title.setFont(font)
    title.setStyleSheet("color: #ffffff; background: transparent;")
    header.addWidget(title)
    layout.addWidget(hero)

    table = QFrame()
    table.setAccessibleName("Edition comparison")
    table.setStyleSheet("QFrame#proTable { background: #566378; border: 1px solid #758196; }")
    table.setObjectName("proTable")
    grid = QGridLayout(table)
    grid.setContentsMargins(1, 1, 1, 1)
    grid.setSpacing(1)
    for column, stretch in enumerate((23, 37, 40)):
        grid.setColumnStretch(column, stretch)
    for row, values in enumerate(ROWS):
        for column, value in enumerate(values):
            cell = QLabel(value)
            cell.setTextFormat(Qt.TextFormat.PlainText)
            cell.setWordWrap(True)
            policy = cell.sizePolicy()
            policy.setHorizontalPolicy(QSizePolicy.Policy.Ignored)
            cell.setSizePolicy(policy)
            cell.setMargin(8)
            background = "#303d61" if column == 2 else "#1d2839"
            weight = "bold" if row == 0 or column == 0 else "normal"
            cell.setStyleSheet(f"color: #f4f6ff; background: {background}; font-weight: {weight};")
            if row and column:
                cell.setAccessibleName(f"{values[0]}, {ROWS[0][column]}, {value}")
            grid.addWidget(cell, row, column)
    layout.addWidget(table)
    note = QLabel(PRICE_NOTE)
    note.setWordWrap(True)
    layout.addWidget(note)
