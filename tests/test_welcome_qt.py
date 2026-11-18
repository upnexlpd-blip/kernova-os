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
    from PySide6.QtWidgets import QApplication, QDialog, QLabel, QListWidget, QStackedWidget, QTextBrowser
except ImportError as exc:
    raise unittest.SkipTest(f"PySide6 is unavailable: {exc}") from exc

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

    def test_pages_keyboard_and_compact_geometry(self):
        for locale_name, start in (("en_US", "Getting started"), ("mk_MK", "Први чекори")):
            with self.subTest(locale=locale_name):
                window = self.window(locale_name)
                navigation = window.findChild(QListWidget)
                pages = window.findChild(QStackedWidget)
                self.assertEqual(navigation.count(), 6)
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

    def test_fixed_action_passes_separate_program_and_arguments(self):
        window = self.window("en_US")
        with patch("system_info.Action.missing_package", return_value=None), patch.object(
            welcome.QProcess, "startDetached", return_value=(True, 42)
        ) as start:
            window.launch("network")
            start.assert_called_once_with("/usr/bin/systemsettings", ["kcm_networkmanagement"])

    def test_compressed_guide_opens_in_native_reader(self):
        guide = self.directory / "user-guide.md"
        with gzip.open(guide.with_suffix(".md.gz"), "wt", encoding="utf-8") as stream:
            stream.write("# Offline instructions\n\nSample content from the bundled guide.\n")
        with patch.object(welcome, "GUIDE_FILE", guide):
            window = self.window("en_US")
        rendered = []

        def read_dialog():
            dialog = window.findChild(QDialog)
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
