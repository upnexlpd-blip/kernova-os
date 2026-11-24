"""Native desktop controls shared by the light and dark layouts."""

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPainter
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from appearance import icon


def brand_icon():
    share = Path(__file__).resolve().parents[2]
    for file in (share / "branding/kernova-ai.svg", share / "icons/hicolor/scalable/apps/kernova-ai.svg"):
        if file.is_file():
            return QIcon(str(file))
    return QIcon.fromTheme("kernova-ai")


class Mark(QLabel):
    def __init__(self, size):
        super().__init__()
        self.mark = brand_icon()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_size(size)

    def set_size(self, size):
        self.setFixedSize(size, size)
        self.setPixmap(self.mark.pixmap(QSize(size, size), self.devicePixelRatioF()))


class ModeTabs(QWidget):
    currentIndexChanged = Signal(int)
    names = ("Chat", "Support", "Code")

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        self.group = QButtonGroup(self)
        for index, name in enumerate(self.names):
            tab = QPushButton(name)
            tab.setObjectName("modeTab")
            tab.setCheckable(True)
            tab.setAccessibleName(name)
            tab.setToolTip(name)
            tab.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
            tab.setIconSize(QSize(23, 23))
            tab.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(tab)
            self.group.addButton(tab, index)
        self.group.button(0).setChecked(True)
        self.group.idToggled.connect(self.toggled)

    def toggled(self, index, checked):
        if checked:
            self.currentIndexChanged.emit(index)

    def currentText(self):
        return self.names[self.group.checkedId()]

    def setCurrentText(self, name):
        if name in self.names:
            self.group.button(self.names.index(name)).setChecked(True)

    def compact(self, enabled):
        for index, name in enumerate(self.names):
            self.group.button(index).setText("" if enabled else name)

    def recolor(self, theme):
        for index, name in enumerate(self.names):
            tab = self.group.button(index)
            tab.setIcon(icon(name.lower(), theme, tab.isChecked()))


class ModelPicker(QComboBox):
    """Show readable model names while preserving exact Ollama identifiers."""
    labels = {"qwen2.5-coder:7b": "Qwen 2.5 Coder · 7B", "qwen2.5-coder:3b": "Qwen 2.5 Coder · 3B",
              "qwen2.5:1.5b": "Qwen 2.5 · 1.5B"}

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        icon("chevron", self.window().theme).paint(painter, self.width() - 28, (self.height() - 17) // 2, 17, 17)
        painter.end()

    def set_models(self, names, preferred):
        self.clear()
        for name in names:
            self.addItem(self.labels.get(name, name), name)
            self.setItemData(self.count() - 1, name, Qt.ItemDataRole.ToolTipRole)
        if names:
            self.setCurrentIndex(0)
        if preferred in names:
            self.setCurrentText(preferred)

    def currentText(self):
        return self.currentData() or ""

    def setCurrentText(self, name):
        index = self.findData(name)
        if index >= 0:
            self.setCurrentIndex(index)


class PromptEdit(QPlainTextEdit):
    submitted = Signal()

    def keyPressEvent(self, event):
        if (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.submitted.emit()
            event.accept()
        else:
            super().keyPressEvent(event)


class SettingsDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        t = owner.t
        self.setWindowTitle(t("settings"))
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        form = QFormLayout()
        self.theme = QComboBox()
        for name in ("light", "dark"):
            self.theme.addItem(t(name), name)
        self.theme.setCurrentIndex(self.theme.findData(owner.theme))
        form.addRow(t("appearance"), self.theme)
        self.language = QComboBox()
        self.language.addItem("English", "en")
        self.language.addItem("Македонски", "mk")
        self.language.setCurrentIndex(self.language.findData(t.language))
        form.addRow(t("language"), self.language)
        layout.addLayout(form)
        self.notice = QLabel(t("language_restart"))
        self.notice.setWordWrap(True)
        self.notice.hide()
        self.language.currentIndexChanged.connect(
            lambda: self.notice.setVisible(self.language.currentData() != t.language))
        layout.addWidget(self.notice)
        footer = QHBoxLayout()
        footer.addStretch()
        cancel = QPushButton(t("cancel"))
        cancel.clicked.connect(self.reject)
        save = QPushButton(t("save"))
        save.setDefault(True)
        save.clicked.connect(self.accept)
        footer.addWidget(cancel)
        footer.addWidget(save)
        layout.addLayout(footer)
