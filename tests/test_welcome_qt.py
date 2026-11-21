"""Optional offscreen integration tests against the Qt widget application."""

import gzip
from io import StringIO
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


APP = Path(__file__).resolve().parents[1] / "apps" / "welcome"
sys.path.insert(0, str(APP))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QEvent, QSettings, Qt, QThreadPool, QTimer
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import (
        QApplication, QComboBox, QDialog, QLabel, QListWidget, QPushButton, QScrollArea, QStackedWidget,
        QTextBrowser,
    )
except ImportError as exc:
    raise unittest.SkipTest(f"PySide6 is unavailable: {exc}") from exc

import ai_tools
import main as welcome  # noqa: E402


SYSTEM = {
    "base": "Debian GNU/Linux 13 (trixie)",
    "session": "live",
    "kernel": "6.12.0",
    "architecture": "x86_64",
    "cpu": "A sample virtual CPU",
    "memory": 8323072,
    "graphics": None,
}


class WelcomeQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["welcome-test"])

    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.settings = QSettings(str(self.directory / "welcome.ini"), QSettings.Format.IniFormat)
        self.product = welcome.string_mapping(APP.parents[1] / "product.json")
        probe = patch.object(welcome, "collect_system_info", return_value=SYSTEM)
        probe.start()
        self.addCleanup(probe.stop)

    def window(self, locale_name):
        messages = welcome.Messages(locale_name)
        window = welcome.WelcomeWindow(self.settings, messages, self.product)
        self.addCleanup(window.close)
        window.show()
        self.assertTrue(QThreadPool.globalInstance().waitForDone(3000))
        self.app.processEvents()
        return window

    def test_application_buttons_have_offline_icons_in_both_languages(self):
        for locale in ("mk_MK", "en_US"):
            window = self.window(locale)
            buttons = {button.text(): button for button in window.findChildren(QPushButton)}
            for key in ("chrome", "viber", "telegram", "whatsapp", "browser", "files", "editor", "terminal"):
                with self.subTest(locale=locale, app=key):
                    icon = buttons[window.t(key)].icon()
                    self.assertFalse(icon.pixmap(28, 28).isNull())
            window.close()

    def test_pages_keyboard_and_compact_geometry(self):
        for locale_name, start in (("en_US", "Getting started"), ("mk_MK", "Први чекори")):
            with self.subTest(locale=locale_name):
                window = self.window(locale_name)
                navigation = window.findChild(QListWidget)
                pages = window.findChild(QStackedWidget)
                self.assertEqual(navigation.count(), 7)
                self.assertEqual(navigation.item(3).text(), "Kernova 2.0 Pro")
                pro_page = pages.widget(3)
                self.assertIn("€29 one-time", [item.text() for item in pro_page.findChildren(QLabel)])
                self.assertEqual(navigation.currentItem().text(), start)
                release = window.t("preview_release", version=self.product["version"])
                self.assertIn(
                    window.t("identity", name=self.product["name"], release=release),
                    [item.text() for item in window.findChildren(QLabel)],
                )
                self.assertEqual(window.start_heading.text(), window.t("live_session"))
                self.assertEqual(window.info["cpu"].text(), SYSTEM["cpu"])
                self.assertEqual(window.info["graphics"].text(), window.t("unavailable"))
                if locale_name == "mk_MK":
                    self.assertIn("7,9", window.info["memory"].text())
                else:
                    self.assertIn("7.9", window.info["memory"].text())
                for width, height in ((900, 570), (863, 460), (647, 332)):
                    # Nominal 1366×768 at 100%, 150%, and 200% with desktop margins.
                    window.resize(width, height)
                    self.app.processEvents()
                    self.assertEqual((window.width(), window.height()), (width, height))
                    navigation.setCurrentRow(0)
                    for page_index in range(pages.count()):
                        self.app.processEvents()
                        self.assertEqual(pages.currentIndex(), page_index)
                        self.assertEqual(
                            pages.currentWidget().horizontalScrollBar().maximum(), 0,
                            f"{locale_name} at {width}×{height}, {navigation.currentItem().text()}",
                        )
                        if page_index < pages.count() - 1:
                            self.app.sendEvent(navigation, QKeyEvent(
                                QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier
                            ))
                window.close()

    def test_autostart_choice_persists_and_menu_enters_gui(self):
        window = self.window("en_US")
        self.assertTrue(window.autostart.isChecked())
        window.autostart.setChecked(False)
        fresh_settings = QSettings(self.settings.fileName(), QSettings.Format.IniFormat)
        self.assertFalse(fresh_settings.value(welcome.AUTOSTART_KEY, True, type=bool))
        # On Windows there is no geteuid, so add it temporarily for the Linux check.
        with patch.object(welcome.os, "geteuid", return_value=1000, create=True), patch.object(
            welcome, "QSettings", wraps=QSettings
        ) as settings_type, patch.object(welcome, "QApplication") as app_type:
            settings_type.return_value = fresh_settings
            with patch.object(sys, "argv", ["kernova-welcome", "--autostart"]):
                self.assertEqual(welcome.main(), 0)
                app_type.assert_not_called()
            app_type.side_effect = RuntimeError("GUI startup begins")
            with patch.object(sys, "argv", ["kernova-welcome"]), self.assertRaisesRegex(
                RuntimeError, "GUI startup begins"
            ):
                welcome.main()

    def test_phone_sharing_starts_only_when_requested(self):
        for locale_name in ("en_US", "mk_MK"):
            with self.subTest(locale=locale_name), patch(
                "system_info.Action.missing_package", return_value=None
            ), patch.object(welcome.QProcess, "startDetached", return_value=(True, 42)) as start:
                window = self.window(locale_name)
                page = window.findChild(QStackedWidget).currentWidget()
                self.assertIn(window.t("connect_phone_help"), [item.text() for item in page.findChildren(QLabel)])
                start.assert_not_called()
                self.button(page, window.t("connect_phone")).click()
                start.assert_called_once_with("/usr/bin/krfb", [])
                window.close()

    def test_fixed_action_passes_separate_program_and_arguments(self):
        window = self.window("en_US")
        with patch("system_info.Action.missing_package", return_value=None), patch.object(
            welcome.QProcess, "startDetached", return_value=(True, 42)
        ) as start:
            window.launch("network")
            start.assert_called_once_with("/usr/bin/systemsettings", ["kcm_networkmanagement"])

    def test_settings_selector_opens_native_modules_and_marks_missing_modules(self):
        with patch("system_info.Action.missing_package", return_value=None) as missing, patch.object(
            welcome.QProcess, "startDetached", return_value=(True, 42)
        ) as start:
            window = self.window("mk_MK")
            window.findChild(QListWidget).setCurrentRow(welcome.PAGES.index("personalize"))
            page = window.findChild(QStackedWidget).currentWidget()
            categories = page.findChild(QComboBox)
            open_button = self.button(page, window.t("settings_open"))
            self.assertEqual(categories.count(), len(welcome.SETTINGS_MODULES))
            for key, (module, _) in welcome.SETTINGS_MODULES.items():
                with self.subTest(category=key):
                    categories.setCurrentIndex(categories.findData(key))
                    self.assertEqual(categories.currentText(), window.t(key))
                    start.reset_mock()
                    open_button.click()
                    start.assert_called_once_with("/usr/bin/systemsettings", [module])
            missing.return_value = "kaccounts-integration"
            categories.setCurrentIndex(categories.findData("account_settings"))
            self.assertFalse(open_button.isEnabled())
            self.assertEqual(open_button.toolTip(), window.t("requires", package="kaccounts-integration"))

    def test_drivers_show_detected_hardware_and_open_requested_download(self):
        for locale_name in ("en_US", "mk_MK"):
            with self.subTest(locale=locale_name), patch(
                "system_info.Action.missing_package", return_value=None
            ), patch.object(welcome.QDesktopServices, "openUrl", return_value=True) as open_url:
                window = self.window(locale_name)
                window.resize(647, 332)
                window.apply_info({**SYSTEM, "graphics": "Virtio GPU"})
                window.findChild(QListWidget).setCurrentRow(welcome.PAGES.index("system"))
                page = window.findChild(QStackedWidget).currentWidget()
                self.button(page, window.t("drivers")).click()
                self.app.processEvents()
                dialog = window.drivers_dialog
                self.assertTrue(dialog.isVisible())
                self.assertEqual(dialog.findChild(QScrollArea).horizontalScrollBar().maximum(), 0)
                self.assertEqual(window.driver_info["cpu"].text(), SYSTEM["cpu"])
                self.assertEqual(window.driver_info["graphics"].text(), "Virtio GPU")
                open_url.assert_not_called()
                for links in welcome.DRIVER_DOWNLOADS.values():
                    for key, url in links.items():
                        self.button(dialog, window.t(key)).click()
                        self.assertEqual(open_url.call_args.args[0].toString(), url)
                with patch.object(welcome.QProcess, "startDetached", return_value=(True, 42)) as start:
                    self.button(dialog, window.t("updates")).click()
                    start.assert_called_once_with("/usr/bin/plasma-discover", ["--mode", "update"])
                self.button(dialog, window.t("close")).click()
                self.assertFalse(dialog.isVisible())

    def test_driver_launcher_selects_system_and_ignores_sign_in_preference(self):
        self.settings.setValue(welcome.AUTOSTART_KEY, False)
        window_class = welcome.WelcomeWindow
        windows = []

        def create_window(*args, **kwargs):
            window = window_class(*args, **kwargs)
            windows.append(window)
            self.addCleanup(window.close)
            return window

        with patch.object(sys, "argv", ["kernova-welcome", "--drivers"]), patch.object(
            welcome.os, "geteuid", return_value=1000, create=True
        ), patch.object(welcome, "QSettings", wraps=QSettings) as settings_type, patch.object(
            welcome, "QApplication", return_value=self.app
        ), patch.object(welcome, "WelcomeWindow", side_effect=create_window), patch.object(
            self.app, "exec", return_value=0
        ):
            settings_type.return_value = self.settings
            self.assertEqual(welcome.main(), 0)
            window = windows[0]
            self.assertEqual(window.findChild(QListWidget).currentRow(), welcome.PAGES.index("system"))
            self.assertTrue(window.drivers_dialog.isVisible())
            self.assertTrue(QThreadPool.globalInstance().waitForDone(3000))

    def test_get_apps_buttons_launch_the_catalog(self):
        with patch("system_info.Action.missing_package", return_value=None), patch.object(
            welcome.QProcess, "startDetached", return_value=(True, 42)
        ) as start:
            window = self.window("mk_MK")
            window.findChild(QListWidget).setCurrentRow(welcome.PAGES.index("apps"))
            page = window.findChild(QStackedWidget).currentWidget()
            for key in ("software", "chrome", "viber", "telegram", "whatsapp"):
                start.reset_mock()
                self.button(page, window.t(key)).click()
                start.assert_called_once_with("/usr/bin/kernova-get-apps", [] if key == "software" else [key])

    @staticmethod
    def button(parent, text):
        return next(button for button in parent.findChildren(QPushButton) if button.text() == text)

    def test_compressed_guide_opens_in_native_reader(self):
        guide = self.directory / "user-guide.md"
        with gzip.open(guide.with_suffix(".md.gz"), "wt", encoding="utf-8") as stream:
            stream.write("# Offline instructions\n\nSample content from the bundled guide.\n")
        with patch.object(welcome, "GUIDE_FILE", guide):
            window = self.window("en_US")
        rendered = []

        def read_dialog():
            dialog = next(dialog for dialog in window.findChildren(QDialog) if dialog.isVisible())
            try:
                rendered.append(dialog.findChild(QTextBrowser).toPlainText())
            finally:
                dialog.accept()

        QTimer.singleShot(0, read_dialog)
        window.show_guide()
        self.assertIn("Sample content from the bundled guide.", rendered[0])

    def test_installed_and_unknown_states_display_truthful_status(self):
        window = self.window("en_US")
        for state in ("installed", "unknown"):
            window.apply_info({**SYSTEM, "session": state})
            self.assertEqual(window.start_text.text(), window.t(f"{state}_intro"))
            self.assertEqual(window.info["session"].text(), window.t(f"{state}_session"))

    @unittest.skipUnless(Path("/bin/sh").is_file(), "requires a POSIX shell")
    def test_ai_install_shows_results_and_allows_retry(self):
        with patch.dict(os.environ, {"HOME": str(self.directory), "PATH": "/usr/bin:/bin"}):
            window = ai_tools.AIToolsWindow("en_US")
            self.addCleanup(window.close)
            window.show()
            name, button = window.buttons["codex"]
            for command, result in (("echo failed; exit 1", "failed"), (
                'mkdir -p "$HOME/.local/bin"; touch "$HOME/.local/bin/codex"; '
                'chmod +x "$HOME/.local/bin/codex"; echo ready', "installed"
            )):
                with patch.object(ai_tools, "INSTALL", command):
                    button.click()
                    self.assertFalse(button.isEnabled())
                    self.assertTrue(window.progress.isVisible())
                    self.assertTrue(window.process.waitForFinished(5000))
                    self.app.processEvents()
                self.assertEqual(window.status.text(), window.text(result, name=name))
                self.assertTrue(window.output.toPlainText().strip())
                self.assertTrue(button.isEnabled())
            self.assertEqual(button.text(), window.text("launch"))
            with patch.object(ai_tools.QProcess, "startDetached", return_value=(True, 1)) as launch:
                button.click()
                self.assertEqual(launch.call_args.args[1][-1], str(self.directory / ".local/bin/codex"))

    def test_root_never_enters_gui(self):
        with patch.object(sys, "argv", ["kernova-welcome"]), patch.object(
            welcome.os, "geteuid", return_value=0, create=True
        ), patch.object(welcome, "QApplication") as app_type, patch.object(
            sys, "stderr", new_callable=StringIO
        ) as stderr:
            self.assertEqual(welcome.main(), 1)
            self.assertTrue(stderr.getvalue())
            app_type.assert_not_called()


if __name__ == "__main__":
    unittest.main()
