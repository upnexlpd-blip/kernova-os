"""KERNOVA Welcome, a native Qt desktop guide."""

import argparse
import gzip
import os
from pathlib import Path
import sys

from PySide6.QtCore import QLocale, QObject, QProcess, QRunnable, QSettings, QSize, Qt, QThreadPool, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel,
    QListWidget, QMessageBox, QPushButton, QScrollArea, QStackedWidget,
    QTextBrowser, QVBoxLayout, QWidget,
)

from system_info import ACTIONS, SETTINGS_MODULES, collect_system_info, language_for, string_mapping


LOCALES_DIR = Path(__file__).resolve().parent / "locales"
PRODUCT_FILE = Path("/usr/share/kernova/product.json")
GUIDE_FILE = Path("/usr/share/doc/kernova-welcome/user-guide.md")
ICON_NAME = "kernova-logo"
ICON_FILE = Path("/usr/share/icons/hicolor/scalable/apps/kernova-logo.svg")
PAGES = ("start", "personalize", "apps", "system", "help", "credits")
SYSTEM_FIELDS = ("base", "session", "kernel", "architecture", "cpu", "memory", "graphics")
AUTOSTART_KEY = "showAtLogin"
DEBIAN_DOWNLOADS = "https://packages.debian.org/trixie"
DRIVER_DOWNLOADS = {
    "cpu": {
        "amd_microcode": f"{DEBIAN_DOWNLOADS}/amd64/amd64-microcode/download",
        "intel_microcode": f"{DEBIAN_DOWNLOADS}/amd64/intel-microcode/download",
    },
    "graphics": {
        "amd_firmware": f"{DEBIAN_DOWNLOADS}/all/firmware-amd-graphics/download",
        "intel_firmware": f"{DEBIAN_DOWNLOADS}/all/firmware-intel-graphics/download",
        "nvidia_firmware": f"{DEBIAN_DOWNLOADS}/all/firmware-nvidia-graphics/download",
        "nvidia_guide": "https://wiki.debian.org/NvidiaGraphicsDrivers/",
    },
}


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
    def __init__(self, settings: QSettings, messages: Messages, product: dict[str, str],
                 initial_page: str = "start"):
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
        navigation.setCurrentRow(PAGES.index(initial_page))
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

    def add_action(self, layout: QVBoxLayout, key: str, *, app_icon: bool = False):
        button = QPushButton(self.t(key))
        if app_icon:
            button.setIcon(QIcon(str(Path(__file__).with_name("icons") / f"{key}.svg")))
            button.setIconSize(QSize(28, 28))
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
        self.add_action(layout, "settings")
        layout.addWidget(label(self.t("personalize_text")))
        category = QComboBox()
        category.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        category.setMinimumContentsLength(12)
        category_label = label(self.t("settings_category"))
        category_label.setBuddy(category)
        category.setAccessibleName(category_label.text())
        for key in SETTINGS_MODULES:
            category.addItem(self.t(key), key)
        layout.addWidget(category_label)
        layout.addWidget(category)
        open_category = QPushButton(self.t("settings_open"))
        open_category.clicked.connect(lambda: self.launch(category.currentData()))
        layout.addWidget(open_category, alignment=Qt.AlignmentFlag.AlignLeft)
        unavailable = label("")
        layout.addWidget(unavailable)

        def update_selection():
            missing = ACTIONS[category.currentData()].missing_package()
            reason = self.t("requires", package=missing) if missing else ""
            open_category.setEnabled(missing is None)
            open_category.setToolTip(reason)
            category.setAccessibleDescription(reason)
            unavailable.setText(reason)
            unavailable.setVisible(missing is not None)

        category.currentIndexChanged.connect(update_selection)
        update_selection()

    def build_apps(self, layout: QVBoxLayout):
        self.add_action(layout, "software")
        layout.addWidget(label(self.t("apps_text")))
        for key in ("chrome", "viber", "telegram", "whatsapp"):
            self.add_action(layout, key, app_icon=True)
        layout.addWidget(label(self.t("whatsapp_note")))
        layout.addWidget(heading(self.t("installed_apps"), 1.15))
        for key in ("browser", "files", "editor", "terminal"):
            self.add_action(layout, key, app_icon=True)

    def add_system_field(self, layout: QVBoxLayout, key: str) -> QLabel:
        name = self.t(key)
        value = label("…")
        value.setAccessibleName(name)
        value.setAccessibleDescription(self.t("loading"))
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse
                                      | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        field = QVBoxLayout()
        field.setSpacing(2)
        field.addWidget(heading(name, 1))
        field.addWidget(value)
        layout.addLayout(field)
        return value

    def build_system(self, layout: QVBoxLayout):
        self.drivers_dialog = self.build_drivers_dialog()
        drivers = QPushButton(self.t("drivers"))
        drivers.clicked.connect(self.show_drivers)
        layout.addWidget(drivers, alignment=Qt.AlignmentFlag.AlignLeft)
        self.info = {key: self.add_system_field(layout, key) for key in SYSTEM_FIELDS}
        self.add_action(layout, "info")

    def build_drivers_dialog(self) -> QDialog:
        dialog = QDialog(self)
        dialog.setWindowTitle(self.t("drivers"))
        layout = QVBoxLayout(dialog)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAccessibleName(self.t("drivers"))
        panel = QWidget()
        content = QVBoxLayout(panel)
        content.setSpacing(8)
        content.addWidget(heading(self.t("drivers"), 1.35))
        self.driver_info = {key: self.add_system_field(content, key) for key in DRIVER_DOWNLOADS}
        content.addWidget(label(self.t("drivers_intro")))
        content.addWidget(label(self.t("drivers_vm")))
        self.add_action(content, "updates")
        content.addWidget(heading(self.t("drivers_downloads"), 1.15))
        content.addWidget(label(self.t("drivers_download_help")))
        for field, links in DRIVER_DOWNLOADS.items():
            content.addWidget(heading(self.t(f"{field}_downloads"), 1))
            for key, url in links.items():
                button = QPushButton(self.t(key))
                button.clicked.connect(lambda checked=False, link=url: self.open_driver_link(link))
                content.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)
        content.addStretch()
        scroll.setWidget(panel)
        layout.addWidget(scroll)
        close = QPushButton(self.t("close"))
        close.clicked.connect(dialog.accept)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        return dialog

    @Slot()
    def show_drivers(self):
        self.drivers_dialog.resize(min(660, self.width() - 36), self.height() - 30)
        self.drivers_dialog.open()

    def open_driver_link(self, url: str):
        if not QDesktopServices.openUrl(QUrl(url)):
            QMessageBox.warning(self.drivers_dialog, self.t("drivers"), self.t("driver_link_failed"))

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
            if key in self.driver_info:
                self.driver_info[key].setAccessibleDescription("")
                self.driver_info[key].setText(widget.text())

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
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--autostart", action="store_true")
    modes.add_argument("--drivers", action="store_true", help="open CPU and graphics driver downloads")
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
    window = WelcomeWindow(settings, messages, string_mapping(PRODUCT_FILE),
                           initial_page="system" if args.drivers else "start")
    desktop = app.primaryScreen().availableGeometry()
    window.resize(min(900, desktop.width() - 36), min(570, desktop.height() - 52))
    window.show()
    if args.drivers:
        window.show_drivers()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
