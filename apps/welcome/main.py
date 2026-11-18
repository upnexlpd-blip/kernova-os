"""KERNOVA Welcome, a native Qt desktop guide."""

import argparse
import gzip
import os
from pathlib import Path
import sys

from PySide6.QtCore import QLocale, QObject, QProcess, QRunnable, QSettings, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel,
    QListWidget, QMessageBox, QPushButton, QScrollArea, QStackedWidget,
    QTextBrowser, QVBoxLayout, QWidget,
)

from system_info import ACTIONS, collect_system_info, language_for, string_mapping


LOCALES_DIR = Path(__file__).resolve().parent / "locales"
PRODUCT_FILE = Path("/usr/share/kernova/product.json")
GUIDE_FILE = Path("/usr/share/doc/kernova-welcome/user-guide.md")
ICON_NAME = "kernova-logo"
ICON_FILE = Path("/usr/share/icons/hicolor/scalable/apps/kernova-logo.svg")
PAGES = ("start", "personalize", "apps", "system", "help", "credits")
SYSTEM_FIELDS = ("base", "session", "kernel", "architecture", "cpu", "memory", "graphics")
AUTOSTART_KEY = "showAtLogin"


class Messages:
    def __init__(self, locale_name: str):
        self.locale = QLocale(locale_name)
        language = language_for(locale_name)
        self.strings = string_mapping(LOCALES_DIR / "en.json")
        if language != "en":
            self.strings.update(string_mapping(LOCALES_DIR / f"{language}.json"))

    def __call__(self, key: str, **values) -> str:
        return self.strings[key].format(**values)


def label(text: str) -> QLabel:
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    return widget


def heading(text: str, scale: float) -> QLabel:
    widget = label(text)
    font = QFont(widget.font())
    font.setPointSizeF(font.pointSizeF() * scale)
    font.setBold(True)
    widget.setFont(font)
    return widget


class ProbeSignals(QObject):
    finished = Signal(dict)


class Probe(QRunnable):
    def __init__(self, signals: ProbeSignals):
        super().__init__()
        self.signals = signals

    def run(self):
        self.signals.finished.emit(collect_system_info())


class WelcomeWindow(QWidget):
    def __init__(self, settings: QSettings, messages: Messages, product: dict[str, str]):
        super().__init__()
        self.settings = settings
        self.t = messages
        name = product.get("name") or self.t("product_name")
        version = product.get("version") or self.t("unavailable")
        channel = product.get("channel")
        release = self.t("release", version=version)
        if channel == "development preview":
            release = self.t("preview_release", version=version)
        elif channel:
            release += f" · {channel}"

        title = self.t("title")
        self.setWindowTitle(title)
        self.setMinimumSize(590, 320)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(14)
        icon = QLabel()
        icon.setPixmap(self.windowIcon().pixmap(52))
        icon.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(icon)
        identity = QVBoxLayout()
        identity.setSpacing(3)
        identity.addWidget(heading(title, 1.65))
        identity.addWidget(label(self.t("identity", name=name, release=release)))
        header.addLayout(identity, 1)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(16)
        navigation = QListWidget()
        navigation.setAccessibleName(self.t("navigate"))
        navigation.setSpacing(4)
        navigation.setFixedWidth(max(
            navigation.fontMetrics().horizontalAdvance(self.t(page)) for page in PAGES
        ) + 46)
        body.addWidget(navigation)
        pages = QStackedWidget()
        body.addWidget(pages, 1)
        root.addLayout(body, 1)

        self.guide_path = next((
            path for path in (GUIDE_FILE, GUIDE_FILE.with_suffix(".md.gz"))
            if path.is_file()
        ), None)

        for page in PAGES:
            navigation.addItem(self.t(page))
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setAccessibleName(self.t(page))
            panel = QWidget()
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(6, 2, 13, 8)
            layout.setSpacing(12)
            layout.addWidget(heading(self.t(page), 1.35))
            getattr(self, f"build_{page}")(layout)
            layout.addStretch()
            scroll.setWidget(panel)
            pages.addWidget(scroll)

        navigation.currentRowChanged.connect(pages.setCurrentIndex)
        navigation.setCurrentRow(0)
        navigation.setFocus()

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(separator)
        footer = QHBoxLayout()
        self.autostart = QCheckBox(self.t("autostart"))
        self.autostart.setToolTip(self.t("autostart_hint"))
        self.autostart.setChecked(settings.value(AUTOSTART_KEY, True, type=bool))
        self.autostart.toggled.connect(self.save_autostart)
        footer.addWidget(self.autostart)
        footer.addStretch()
        close = QPushButton(self.t("close"))
        close.clicked.connect(self.close)
        footer.addWidget(close)
        root.addLayout(footer)

        self.probe_signals = ProbeSignals()
        self.probe_signals.finished.connect(self.apply_info)
        QThreadPool.globalInstance().start(Probe(self.probe_signals))

    def save_autostart(self, enabled: bool):
        self.settings.setValue(AUTOSTART_KEY, enabled)
        self.settings.sync()
        if self.settings.status() != QSettings.Status.NoError:
            self.autostart.setEnabled(False)
            self.autostart.setAccessibleDescription(self.t("save_failed"))
            QMessageBox.warning(self, self.t("title"), self.t("save_failed"))

    def add_action(self, layout: QVBoxLayout, key: str):
        button = QPushButton(self.t(key))
        button.clicked.connect(lambda checked=False: self.launch(key))
        missing = ACTIONS[key].missing_package()
        if missing is not None:
            reason = self.t("requires", package=missing)
            button.setToolTip(reason)
            button.setAccessibleDescription(reason)
            button.setEnabled(False)
            layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(label(reason))
        else:
            layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)

    def launch(self, key: str):
        action = ACTIONS[key]
        if action.missing_package() is None:
            started, _ = QProcess.startDetached(action.arguments[0], list(action.arguments[1:]))
            if started:
                return
        QMessageBox.warning(self, self.t("title"), self.t("launch_failed", app=self.t(key)))

    def build_start(self, layout: QVBoxLayout):
        self.start_heading = heading(self.t("loading"), 1.15)
        self.start_text = label(self.t("start_intro"))
        layout.addWidget(self.start_heading)
        layout.addWidget(self.start_text)
        self.add_action(layout, "network")

    def build_personalize(self, layout: QVBoxLayout):
        layout.addWidget(label(self.t("personalize_text")))
        self.add_action(layout, "settings")

    def build_apps(self, layout: QVBoxLayout):
        layout.addWidget(label(self.t("apps_text")))
        for key in ("browser", "files", "editor", "terminal", "software"):
            self.add_action(layout, key)

    def build_system(self, layout: QVBoxLayout):
        self.info = {}
        for key in SYSTEM_FIELDS:
            value = label("…")
            value.setAccessibleDescription(self.t("loading"))
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse
                                          | Qt.TextInteractionFlag.TextSelectableByKeyboard)
            name = self.t(key)
            value.setAccessibleName(name)
            field = QVBoxLayout()
            field.setSpacing(2)
            field.addWidget(heading(name, 1))
            field.addWidget(value)
            layout.addLayout(field)
            self.info[key] = value
        self.add_action(layout, "info")

    @Slot(dict)
    def apply_info(self, results: dict):
        session = results["session"]
        self.start_heading.setText(self.t(f"{session}_session"))
        self.start_text.setText(self.t(f"{session}_intro"))
        for key, widget in self.info.items():
            value = results.get(key)
            if key == "session":
                value = self.t(f"{session}_session")
            if key == "memory" and isinstance(value, int):
                size = self.t.locale.toString(value / (1024 * 1024), "f", 1)
                value = self.t("gib", size=size)
            widget.setAccessibleDescription("")
            widget.setText(str(value) if value else self.t("unavailable"))

    def build_help(self, layout: QVBoxLayout):
        layout.addWidget(label(self.t("help_text")))
        guide = QPushButton(self.t("guide"))
        guide.clicked.connect(self.show_guide)
        layout.addWidget(guide, alignment=Qt.AlignmentFlag.AlignLeft)
        if self.guide_path is None:
            guide.setEnabled(False)
            guide.setToolTip(self.t("guide_missing"))
            guide.setAccessibleDescription(self.t("guide_missing"))
            layout.addWidget(label(self.t("guide_missing")))

    def show_guide(self):
        try:
            if self.guide_path.suffix == ".gz":
                with gzip.open(self.guide_path, "rt", encoding="utf-8") as stream:
                    text = stream.read()
            else:
                text = self.guide_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError, EOFError):
            QMessageBox.warning(self, self.t("title"), self.t("guide_unreadable"))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(self.t("guide"))
        dialog.resize(self.width() - 36, self.height() - 30)
        layout = QVBoxLayout(dialog)
        viewer = QTextBrowser()
        viewer.setAccessibleName(self.t("guide"))
        viewer.setOpenLinks(False)
        viewer.setMarkdown(text)
        layout.addWidget(viewer)
        close = QPushButton(self.t("close"))
        close.clicked.connect(dialog.accept)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        dialog.exec()

    def build_credits(self, layout: QVBoxLayout):
        layout.addWidget(label(self.t("credits_text")))
        layout.addWidget(label(self.t("licenses")))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--autostart", action="store_true")
    args = parser.parse_args()
    system_locale = QLocale.system()
    messages = Messages(next(iter(system_locale.uiLanguages()), system_locale.name()))
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        print(messages("ordinary_user"), file=sys.stderr)
        return 1
    settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                         "kernova-os", "welcome")
    settings.setFallbacksEnabled(False)
    if args.autostart and not settings.value(AUTOSTART_KEY, True, type=bool):
        return 0

    app = QApplication([sys.argv[0]])
    app.setApplicationName("kernova-welcome")
    app.setApplicationDisplayName(messages("title"))
    app.setDesktopFileName("kernova-welcome")
    app.setWindowIcon(QIcon.fromTheme(ICON_NAME, QIcon(str(ICON_FILE))))
    window = WelcomeWindow(settings, messages, string_mapping(PRODUCT_FILE))
    desktop = app.primaryScreen().availableGeometry()
    window.resize(min(900, desktop.width() - 36), min(570, desktop.height() - 52))
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
