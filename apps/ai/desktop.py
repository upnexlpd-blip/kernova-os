"""Native desktop controls shared by the light and dark layouts."""

from pathlib import Path
import time

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPainter
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QSizePolicy, QStackedWidget, QToolButton,
    QVBoxLayout, QWidget,
)

from appearance import icon


def brand_icon():
    share = Path(__file__).resolve().parents[2]
    for file in (share / "branding/kernova-ai.svg", share / "icons/hicolor/scalable/apps/kernova-ai.svg"):
        if file.is_file():
            return QIcon(str(file))
    return QIcon.fromTheme("kernova-ai")


def format_relative_age(updated_at, now_text="1m"):
    if not updated_at:
        return ""
    delta = max(0, int(time.time()) - int(updated_at))
    if delta < 60:
        return now_text
    if delta < 3600:
        return f"{delta // 60}m"
    if delta < 86400:
        return f"{delta // 3600}h"
    if delta < 86400 * 14:
        return f"{delta // 86400}d"
    return f"{delta // (86400 * 7)}w"


class Mark(QLabel):
    def __init__(self, size):
        super().__init__()
        self.mark = brand_icon()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_size(size)

    def set_size(self, size):
        self.setFixedSize(size, size)
        self.setPixmap(self.mark.pixmap(QSize(size, size), self.devicePixelRatioF()))


class ProjectFolderRow(QWidget):
    """Collapsible project folder header inside the unified Projects tree."""

    def __init__(self, owner, folder_path, collapsed=False):
        super().__init__()
        self.owner = owner
        self.folder_path = folder_path
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(7)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(icon("folder", owner.theme).pixmap(QSize(15, 15)))
        icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        name = Path(folder_path).name or folder_path
        title = QLabel(name)
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lay.addWidget(icon_lbl)
        lay.addWidget(title, 1)
        if collapsed:
            arrow = QLabel("›")
            arrow.setObjectName("rowAge")
            arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            lay.addWidget(arrow)
        self.setToolTip(folder_path)

    def contextMenuEvent(self, event):
        self.owner.show_project_context_menu(self.folder_path, event.globalPos())


class ConversationRow(QWidget):
    """Indented conversation row showing relative age normally and Archive / Pin / More on hover."""

    def __init__(self, owner, chat_id, title_text, meta, *, indented=False):
        super().__init__()
        self.owner = owner
        self.chat_id = chat_id
        self.raw_title = title_text
        self.menu_open = False
        self.setMouseTracking(True)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(22 if indented else 8, 3, 5, 3)
        lay.setSpacing(5)

        if meta.get("unread"):
            dot = QLabel("•")
            dot.setObjectName("unreadDot")
            dot.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            lay.addWidget(dot)

        if meta.get("pinned"):
            pin_mark = QLabel()
            pin_mark.setPixmap(icon("pin", owner.theme, True).pixmap(QSize(12, 12)))
            pin_mark.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            lay.addWidget(pin_mark)

        self.title_label = QLabel()
        self.title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lay.addWidget(self.title_label, 1)

        self.right_stack = QStackedWidget()
        self.right_stack.setFixedHeight(20)

        age_page = QWidget()
        age_page.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        age_lay = QHBoxLayout(age_page)
        age_lay.setContentsMargins(2, 0, 2, 0)
        self.age_label = QLabel(format_relative_age(meta.get("updated_at", 0), "1m"))
        self.age_label.setObjectName("rowAge")
        self.age_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.age_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        age_lay.addWidget(self.age_label)
        self.right_stack.addWidget(age_page)

        actions_page = QWidget()
        act_lay = QHBoxLayout(actions_page)
        act_lay.setContentsMargins(0, 0, 0, 0)
        act_lay.setSpacing(2)

        self.archive_btn = QPushButton("")
        self.archive_btn.setObjectName("rowAction")
        self.archive_btn.setIcon(icon("archive", owner.theme))
        self.archive_btn.setIconSize(QSize(13, 13))
        self.archive_btn.setToolTip(owner.t("unarchive_chat" if meta.get("archived") else "archive_chat"))
        self.archive_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.archive_btn.clicked.connect(lambda: owner.toggle_archive_chat(chat_id))

        self.pin_btn = QPushButton("")
        self.pin_btn.setObjectName("rowAction")
        self.pin_btn.setIcon(icon("pin", owner.theme, bool(meta.get("pinned"))))
        self.pin_btn.setIconSize(QSize(13, 13))
        self.pin_btn.setToolTip(owner.t("unpin_chat" if meta.get("pinned") else "pin_chat"))
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_btn.clicked.connect(lambda: owner.toggle_pin_chat(chat_id))

        self.more_btn = QToolButton()
        self.more_btn.setObjectName("rowAction")
        self.more_btn.setIcon(icon("more", owner.theme))
        self.more_btn.setIconSize(QSize(13, 13))
        self.more_btn.setToolTip(owner.t("settings"))
        self.more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.more_btn.clicked.connect(self._open_more_menu)

        act_lay.addWidget(self.archive_btn)
        act_lay.addWidget(self.pin_btn)
        act_lay.addWidget(self.more_btn)
        self.right_stack.addWidget(actions_page)

        lay.addWidget(self.right_stack)
        self._update_elided_title()

    def _update_elided_title(self):
        avail = max(60, self.title_label.width() or 128)
        metrics = self.title_label.fontMetrics()
        self.title_label.setText(metrics.elidedText(self.raw_title, Qt.TextElideMode.ElideRight, avail))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided_title()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.right_stack.setCurrentIndex(1)
        self._update_elided_title()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if not self.menu_open:
            self.right_stack.setCurrentIndex(0)
            self._update_elided_title()

    def _open_more_menu(self):
        self.menu_open = True
        self.right_stack.setCurrentIndex(1)
        pos = self.more_btn.mapToGlobal(self.more_btn.rect().bottomLeft())
        try:
            self.owner.show_chat_context_menu(self.chat_id, pos)
        finally:
            self.menu_open = False
            if not self.underMouse():
                self.right_stack.setCurrentIndex(0)

    def contextMenuEvent(self, event):
        self.menu_open = True
        self.right_stack.setCurrentIndex(1)
        try:
            self.owner.show_chat_context_menu(self.chat_id, event.globalPos())
        finally:
            self.menu_open = False
            if not self.underMouse():
                self.right_stack.setCurrentIndex(0)


class ModeTabs(QWidget):
    currentIndexChanged = Signal(int)
    names = ("Chat", "Support", "Code")

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.group = QButtonGroup(self)
        for index, name in enumerate(self.names):
            tab = QPushButton(name)
            tab.setObjectName("modeTab")
            tab.setCheckable(True)
            tab.setAccessibleName(name)
            tab.setToolTip(name)
            tab.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
            tab.setIconSize(QSize(15, 15))
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
    labels = {
        "qwen2.5-coder:7b": "Qwen 2.5 Coder · 7B",
        "qwen2.5-coder:3b": "Qwen 2.5 Coder · 3B",
        "qwen2.5:1.5b": "Qwen 2.5 · 1.5B",
        "llama3.2:3b": "Llama 3.2 · 3B",
        "deepseek-r1:7b": "DeepSeek R1 · 7B",
        "gemma3:4b": "Gemma 3 · 4B",
        "mistral:7b": "Mistral · 7B",
        "codellama:7b": "CodeLlama · 7B",
        "qwen2.5-coder:14b": "Qwen 2.5 Coder · 14B",
    }

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        theme = getattr(self.window(), "theme", "light")
        icon("chevron", theme).paint(painter, self.width() - 20, (self.height() - 14) // 2, 14, 14)
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
        self.setMinimumWidth(340)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)
        form = QFormLayout()
        form.setSpacing(8)
        self.theme = QComboBox()
        for name in ("light", "dark"):
            self.theme.addItem(t(name), name)
        self.theme.setCurrentIndex(self.theme.findData(owner.theme))
        form.addRow(t("appearance"), self.theme)

        self.font_scale = QComboBox()
        for scale_key in ("compact", "normal", "large"):
            self.font_scale.addItem(t(f"scale_{scale_key}"), scale_key)
        current_scale = getattr(owner, "font_scale", "compact")
        self.font_scale.setCurrentIndex(max(0, self.font_scale.findData(current_scale)))
        form.addRow(t("font_size"), self.font_scale)

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
