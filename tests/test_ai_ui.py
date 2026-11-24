"""Offscreen desktop journeys. The model fixture makes no network requests."""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
from threading import Event
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtCore import QCoreApplication, QEvent, QSettings, QUrl
    from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QPlainTextEdit, QPushButton
except ImportError as exc:
    raise unittest.SkipTest(f"PySide6 is unavailable: {exc}") from exc

APP = Path(__file__).resolve().parents[1] / "apps" / "ai"
spec = importlib.util.spec_from_file_location("kernova_ai_ui_for_test", APP / "main.py")
ui = importlib.util.module_from_spec(spec)
with patch.object(sys, "path", [str(APP), *sys.path]):
    spec.loader.exec_module(ui)


class FixtureClient:
    def __init__(self):
        self.names = []
        self.state = "ready"
        self.requests = []
        self.pulled = []
        self.replacement = "print('updated')\n"
        self.hold_stream = False
        self.release = Event()

    def discover(self):
        return self.state, list(self.names)

    def install(self, entry, token, update):
        self.pulled.append(entry["tag"])
        update("fixture", 5, 10)
        token.check()
        self.names.append(entry["tag"])
        update("fixture", 10, 10)

    def chat(self, model, messages, token, receive, response_format=None):
        self.requests.append((model, messages, response_format))
        if response_format:
            receive(json.dumps({"replacement": self.replacement}))
        else:
            receive("hello ")
            if self.hold_stream:
                while not self.release.wait(0.01):
                    token.check()
            token.check()
            receive("world\n```py\nprint(1)\n```")


class DesktopFlows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["kernova-ai-test"])

    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.client = FixtureClient()
        self.addCleanup(self.client.release.set)
        self.store = ui.History(self.root / "data")
        self.addCleanup(self.store.db.close)
        settings = QSettings(str(self.root / "ai.ini"), QSettings.Format.IniFormat)
        self.enterContext(patch.object(ui, "QSettings", return_value=settings))

    def wait_until(self, condition):
        deadline = time.monotonic() + 5
        while not condition() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.002)
        self.assertTrue(condition(), "Qt worker did not reach expected state within 5 s")

    def window(self, locale="en", store=None):
        window = ui.ChatWindow(ui.Messages(locale), store or self.store, self.client)
        window.show()
        def close_window():
            window.close()
            window.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.app.processEvents()
        self.addCleanup(close_window)
        self.wait_until(lambda: window.job is None)
        return window

    def send(self, window, text):
        window.prompt.setPlainText(text)
        self.assertTrue(window.send_button.isEnabled())
        window.send_button.click()
        self.wait_until(lambda: window.job is None)

    def test_first_run_installs_only_selected_model_in_both_languages(self):
        entries = json.loads((APP / "catalog.json").read_text(encoding="utf-8"))["models"]
        catalog_module = sys.modules[ui.ModelLibrary.__module__]
        with patch.object(catalog_module, "load_catalog", return_value=(entries, None)):
            for language, choose in [("en", "Choose a model"), ("mk", "Избери модел")]:
                with self.subTest(language=language):
                    self.client.names.clear()
                    self.client.pulled.clear()
                    window = self.window(language)
                    self.assertEqual(window.choose.text().casefold(), choose.casefold())
                    self.assertTrue(window.choose.isVisible())
                    window.prompt.setPlainText("first message")
                    self.assertFalse(window.send_button.isEnabled())
                    selected = entries[1]["tag"]

                    def choose_model(dialog):
                        self.wait_until(lambda: dialog.job is None)
                        dialog.listing.setCurrentRow(1)
                        self.assertIn(entries[1]["license"], dialog.details.text())
                        self.assertTrue(dialog.install.isEnabled())
                        dialog.install.click()
                        self.wait_until(lambda: dialog.job is None)
                        self.assertFalse(dialog.install.isEnabled())
                        self.assertTrue(dialog.remove.isEnabled())
                        return QDialog.DialogCode.Accepted

                    # Invoke the slot directly so assertion errors surface in unittest.
                    with patch.object(ui.ModelLibrary, "exec", choose_model):
                        window.open_library()
                    self.wait_until(lambda: window.job is None)
                    self.assertEqual(self.client.pulled, [selected])
                    self.assertEqual(window.models.currentText(), selected)
                    self.assertTrue(window.send_button.isEnabled())
                    self.assertFalse(window.choose.isVisible())
                    window.close()

    def test_service_states_and_retry(self):
        self.client.state = "missing"
        window = self.window("mk")
        self.assertTrue(window.guide.isVisible())
        self.assertTrue(window.refresh.isVisible())
        self.assertEqual(window.status.text(), window.t("missing"))
        self.client.state = "stopped"
        window.refresh.click()
        self.wait_until(lambda: window.job is None)
        self.assertFalse(window.guide.isVisible())
        self.assertIn("systemctl start ollama", window.status.text())
        self.client.state = "ready"
        window.refresh.click()
        self.wait_until(lambda: window.job is None)
        self.assertTrue(window.choose.isVisible())

    def test_stream_stop_copy_reopen_and_confirm_deletion(self):
        self.client.names = ["fixture:local"]
        self.client.hold_stream = True
        window = self.window()
        window.prompt.setPlainText("first")
        window.send_button.click()
        self.wait_until(lambda: window.transcript.partial == "hello ")
        for control in (window.models, window.mode, window.new_button, window.send_button,
                        window.delete_button, window.history):
            self.assertFalse(control.isEnabled())
        self.assertTrue(window.stop_button.isEnabled())
        window.stop_button.click()
        self.wait_until(lambda: window.job is None)
        self.assertIn(window.t("cancelled"), window.transcript.toPlainText())
        self.client.hold_stream = False
        self.send(window, "continue")
        previous = self.client.requests[-1][1]
        self.assertEqual([row["content"] for row in previous[1:]], ["first", "hello ", "continue"])
        window.transcript.copy_block(QUrl("copy:0"))
        self.assertEqual(self.app.clipboard().text(), "print(1)\n")
        window.close()
        reopened = ui.History(self.root / "data")
        self.addCleanup(reopened.db.close)
        window = self.window(store=reopened)
        window.history.setCurrentRow(0)
        self.assertIn("hello world", window.transcript.toPlainText())
        for key, count in (("cancel", 1), ("confirm", 0)):
            def decide(box):
                next(b for b in box.buttons() if b.text() == window.t(key)).click()
                return box.result()

            with patch.object(QMessageBox, "exec", decide):
                window.delete_chat()
            self.assertEqual(len(reopened.list()), count)
        self.assertEqual(window.history.count(), 0)

    def test_code_file_choice_diff_decisions_and_stale_change(self):
        self.client.names = ["fixture:local"]
        project = self.root / "project"
        project.mkdir()
        file = project / "app.py"
        file.write_text("print(1)\n")
        window = self.window("mk")
        window.mode.setCurrentText("Code")
        self.assertFalse(window.edit.isEnabled())
        with patch.object(ui.QFileDialog, "getExistingDirectory", return_value=str(project)):
            window.folder.click()
        self.wait_until(lambda: window.job is None)
        window.files.setCurrentIndex(window.files.findData("app.py"))
        self.assertEqual(window.files.currentData(), "app.py")
        window.edit.setChecked(True)
        for decision, expected in (("reject", "print(1)\n"), ("apply", "print('updated')\n"),
                                   ("stale", "editor data\n")):
            with self.subTest(decision=decision):
                before = file.read_text()
                inspected = []
                if decision == "stale":
                    self.client.replacement = "print('next')\n"

                def decide(dialog):
                    if decision == "stale":
                        file.write_text("editor data\n")
                    diff = dialog.findChild(QPlainTextEdit)
                    inspected.append((diff.toPlainText(), diff.isReadOnly(), file.read_text()))
                    key = "reject" if decision == "reject" else "apply"
                    next(b for b in dialog.findChildren(QPushButton) if b.text() == window.t(key)).click()
                    return dialog.result()

                with patch.object(QDialog, "exec", decide):
                    self.send(window, "Промени го повикот")
                self.assertEqual(len(inspected), 1)
                diff, readonly, observed = inspected[0]
                self.assertTrue(readonly)
                self.assertIn("-" + before.strip(), diff)
                self.assertIn("+" + self.client.replacement.strip(), diff)
                self.assertEqual(observed, expected if decision == "stale" else before)
                self.assertEqual(file.read_text(), expected)
                self.assertEqual(self.client.requests[-1][2], ui.EDIT_FORMAT)
                self.assertIn("app.py", self.client.requests[-1][1][-1]["content"])
                if decision == "stale":
                    self.assertEqual(window.status.text(), window.t("stale_file"))

    def test_deleted_chat_never_rebinds_to_another_window_conversation(self):
        self.client.names = ["fixture:local"]
        other = ui.History(self.root / "data")
        self.addCleanup(other.db.close)
        old = other.send(None, "Chat", self.client.names[0], "Original")
        window = self.window("mk")
        window.history.setCurrentRow(0)
        other.delete(old)
        fresh = other.send(None, "Chat", self.client.names[0], "New")
        self.assertNotEqual(fresh, old)
        self.send(window, "Draft for the missing conversation")
        self.assertEqual(window.status.text(), window.t("chat_removed"))
        self.assertEqual(window.prompt.toPlainText(), "Draft for the missing conversation")
        self.assertEqual([m["content"] for m in other.messages(fresh)], ["New"])
        with self.assertRaises(ui.ChatRemoved):
            self.store.delete(old)
        with self.assertRaises(ui.ChatRemoved):
            self.store.append(old, "assistant", "Late reply")

        # Deletion during streaming also clears the stale view and preserves the new chat.
        window.history.setCurrentRow(0)
        self.client.hold_stream = True
        window.prompt.setPlainText("Slow request")
        window.send_button.click()
        self.wait_until(lambda: window.transcript.partial == "hello ")
        other.delete(fresh)
        newest = other.send(None, "Chat", self.client.names[0], "Independent")
        window.stop_button.click()
        self.wait_until(lambda: window.job is None)
        self.assertIsNone(window.chat_id)
        self.assertEqual(window.status.text(), window.t("chat_removed"))
        self.assertEqual([m["content"] for m in other.messages(newest)], ["Independent"])

    def test_existing_history_initializes_sequence_above_previous_ids(self):
        folder = self.root / "old-data"
        folder.mkdir()
        with sqlite3.connect(folder / "history.sqlite3") as old:
            old.execute("CREATE TABLE chats(id INTEGER PRIMARY KEY,title TEXT,mode TEXT,model TEXT)")
            old.execute("INSERT INTO chats VALUES(47,'existing','Chat','local')")
        old.close()
        upgraded = ui.History(folder)
        self.addCleanup(upgraded.db.close)
        self.assertEqual(upgraded.list()[0][0], 47)
        upgraded.delete(47)
        self.assertGreater(upgraded.send(None, "Chat", "local", "new"), 47)

    def test_support_measures_real_disk_and_requires_exact_confirmation(self):
        self.client.names = ["fixture:local"]
        window = self.window("mk")
        window.mode.setCurrentText("Support")
        self.send(window, "Зошто ми е полн дискот?")
        self.assertEqual(self.client.requests, [])
        messages = self.store.messages(window.chat_id)
        self.assertEqual([m["role"] for m in messages], ["user", "evidence", "assistant"])
        self.assertIn("слободни", messages[-1]["content"])
        self.assertIn("GiB", window.transcript.toPlainText())
        self.send(window, "Спореди го дискот со RAM")
        attachment = self.client.requests[-1][1][-1]["content"].split("Local diagnostic data (JSON): ")[1]
        self.assertIn("слободни", json.loads(attachment))
        self.assertIn("RAM", json.loads(attachment))
        proposal = SimpleNamespace(description="Вклучи го звукот на излезот #42?")
        with patch.object(ui, "prepare_repair", return_value=proposal), patch.object(ui, "apply_repair") as apply:
            for key in ("cancel", "confirm"):
                observed = []

                def decide(box):
                    observed.append(box.text())
                    next(b for b in box.buttons() if b.text() == window.t(key)).click()
                    return box.result()

                with patch.object(QMessageBox, "exec", decide):
                    window.repair.click()
                    self.wait_until(lambda: window.job is None)
                self.assertEqual(observed, [proposal.description])
                if key == "cancel":
                    apply.assert_not_called()
            apply.assert_called_once_with(proposal)

    def test_home_appearance_and_language_survive_restart(self):
        def open_with_preferences():
            # Exercise the launcher's language selection without creating a second QApplication.
            with patch.object(sys, "argv", ["kernova-ai"]), patch.object(ui, "QApplication") as app, \
                    patch.object(ui, "History", return_value=self.store), patch.object(ui, "ChatWindow") as create, \
                    patch.object(os, "geteuid", return_value=1000, create=True):
                app.return_value.exec.return_value = 0
                self.assertEqual(ui.main(), 0)
                language = create.call_args.args[0].language
            return self.window(language)

        def check_hero(window, light):
            self.assertTrue(window.hero_title.isVisible())
            self.assertTrue(window.open_button.isVisible())
            self.assertFalse(window.transcript.isVisible())
            self.assertFalse(window.hero_mark.pixmap().isNull())
            # Check a rendered surface, including stylesheet overrides.
            rendered = window.grab().toImage()
            point = window.hero.mapTo(window, window.hero.rect().topLeft())
            ratio = rendered.devicePixelRatio()
            brightness = rendered.pixelColor(round((point.x() + 2) * ratio),
                                             round((point.y() + 2) * ratio)).lightness()
            if light:
                self.assertGreater(brightness, 180)
            else:
                self.assertLess(brightness, 85)

        self.client.names = ["qwen2.5-coder:7b"]
        window = open_with_preferences()
        self.assertEqual(window.t.language, "en")
        self.assertEqual(window.hero_title.text(), "How can I help?")
        self.assertEqual(window.theme, "light")
        check_hero(window, light=True)

        def change_preferences(dialog):
            dialog.theme.setCurrentIndex(dialog.theme.findData("dark"))
            dialog.language.setCurrentIndex(dialog.language.findData("mk"))
            next(b for b in dialog.findChildren(QPushButton) if b.text() == window.t("save")).click()
            return dialog.result()

        with patch.object(ui.SettingsDialog, "exec", change_preferences):
            window.preferences.click()
        self.assertEqual(window.theme, "dark")
        check_hero(window, light=False)
        window.settings.sync()
        ini = window.settings.fileName()
        window.close()
        with patch.object(ui, "QSettings", side_effect=lambda *_: QSettings(ini, QSettings.Format.IniFormat)):
            reopened = open_with_preferences()
        self.assertEqual(reopened.theme, "dark")
        self.assertEqual(reopened.t.language, "mk")
        self.assertEqual(reopened.hero_title.text(), ui.Messages("mk")("hero_title"))
        check_hero(reopened, light=False)

    def test_mode_buttons_and_open_project_shortcut(self):
        window = self.window()
        tabs = {b.accessibleName(): b for b in window.mode.findChildren(QPushButton)}
        self.assertEqual(set(tabs), {"Chat", "Support", "Code"})
        for mode in ("Support", "Code", "Chat"):
            tabs[mode].click()
            self.assertEqual(window.mode.currentText(), mode)
            self.assertEqual([name for name, tab in tabs.items() if tab.isChecked()], [mode])
            self.assertEqual(window.folder.isVisible(), mode == "Code")
            self.assertEqual(window.repair.isVisible(), mode == "Support")

        project = self.root / "example-project"
        project.mkdir()
        (project / "main.py").write_text("print('test')\n", encoding="utf-8")
        with patch.object(ui.QFileDialog, "getExistingDirectory", return_value=str(project)) as chooser:
            window.open_button.click()
        self.wait_until(lambda: window.job is None)
        chooser.assert_called_once()
        self.assertTrue(tabs["Code"].isChecked())
        self.assertEqual(window.folder.toolTip(), str(project))
        self.assertGreaterEqual(window.files.findData("main.py"), 0)
        self.assertEqual(self.store.list(), [])

    def test_free_disk_shortcut_with_and_without_an_installed_model(self):
        agents = sys.modules[ui.support_answer.__module__]
        volume = agents.DiskUsage("test-volume", 100 * 2**30, 75 * 2**30, 25 * 2**30)
        with patch.object(agents, "_volumes", return_value=[volume]):
            window = self.window()
            popup = []
            with patch.object(QMessageBox, "exec", lambda box: popup.append(box.text())):
                window.disk_button.click()
                self.wait_until(lambda: window.job is None)
            self.assertEqual(window.mode.currentText(), "Support")
            self.assertEqual(len(popup), 1)
            self.assertIn("25.00 GiB free", popup[0])
            self.assertEqual(self.store.list(), [])
            window.close()

            self.client.names = ["qwen2.5-coder:7b"]
            window = self.window()
            window.disk_button.click()
            self.wait_until(lambda: window.job is None)
            self.assertEqual(window.mode.currentText(), "Support")
            self.assertTrue(window.transcript.isVisible())
            messages = self.store.messages(window.chat_id)
            self.assertEqual(messages[0]["content"], window.t("disk_question"))
            self.assertEqual([row["role"] for row in messages], ["user", "evidence", "assistant"])
            self.assertIn("25.00 GiB free", messages[-1]["content"])
            self.assertEqual(self.client.requests, [])

    def test_workspace_panels_intents_navigation_and_custom_pull(self):
        self.client.names = ["qwen2.5-coder:7b"]
        pulled_tags = []

        def fake_pull_tag(raw_tag, token, progress):
            tag = raw_tag if ":" in raw_tag else raw_tag + ":latest"
            progress("pulling", 25, 50)
            token.check()
            pulled_tags.append(tag)
            self.client.names.append(tag)
            progress("success", 50, 50)
            return tag

        self.client.pull_tag = fake_pull_tag
        window = self.window()
        window.resize(1240, 680)
        self.app.processEvents()

        # Compact default font scale (12px) instead of oversized fonts
        self.assertEqual(window.font().pixelSize(), 12)

        # Intent modes (Plan / Test / Ideas) inject structured guidance into system prompt without mutating user text
        window.apply_quick_intent("plan")
        self.assertEqual(window.intent, "plan")
        self.assertTrue(window.chips_row.isVisible())
        self.send(window, "Build a cache module")
        sent_system = self.client.requests[-1][1][0]["content"]
        self.assertIn("step-by-step implementation plan", sent_system)
        self.assertEqual(self.client.requests[-1][1][-1]["content"], "Build a cache module")
        # Step duration metadata is recorded and rendered in transcript
        self.assertTrue(window.transcript.turn_meta)
        self.assertIn("›", window.transcript.toPlainText())

        # Back / Forward navigation across conversations
        first_chat = window.chat_id
        window.new_chat()
        self.assertIsNone(window.chat_id)
        self.assertTrue(window.back_btn.isEnabled())
        window.navigate_back()
        self.assertEqual(window.chat_id, first_chat)
        self.assertTrue(window.forward_btn.isEnabled())
        window.navigate_forward()
        self.assertIsNone(window.chat_id)

        # Workspace panel sections & free Ollama model pull
        for section in ("review", "file", "terminal", "browser", "side", "plugins"):
            window.workspace_pane.open_section(section)
            self.assertTrue(window.workspace_pane.sub_bar.isVisible())
        window.workspace_pane.custom_tag_edit.setText("llama3.2:3b")
        window.workspace_pane._pull_typed_model()
        self.wait_until(lambda: window.workspace_pane.pull_job is None and window.job is None)
        self.assertEqual(pulled_tags, ["llama3.2:3b"])
        self.assertIn("llama3.2:3b", window.names)

        # Top-left sidebar logo is hidden per UI design
        self.assertFalse(window.brand_mark.isVisible())

        # Rename, Pin, Mark Unread, Duplicate, Archive and Nested Projects tree
        project_dir = self.root / "agent"
        project_dir.mkdir()
        (project_dir / "demo.py").write_text("x = 1\n", encoding="utf-8")
        with patch.object(ui.QFileDialog, "getExistingDirectory", return_value=str(project_dir)):
            window.open_project()
        self.wait_until(lambda: window.job is None)
        # First row in unified Projects tree is the folder header ("project", ...), second is the indented chat
        self.assertEqual(window.history.item(0).data(ui.Qt.ItemDataRole.UserRole)[0], "project")
        with patch.object(ui.QInputDialog, "getText", return_value=("Renamed Architecture Chat", True)):
            window.rename_chat_dialog(first_chat, "Build a cache module")
        self.assertEqual(self.store.list()[0][1], "Renamed Architecture Chat")
        window.toggle_pin_chat(first_chat)
        self.assertTrue(self.store.meta_map()[first_chat]["pinned"])
        window.toggle_unread_chat(first_chat)
        self.assertTrue(self.store.meta_map()[first_chat]["unread"])
        window._duplicate_chat(first_chat)
        self.assertEqual(len(self.store.list()), 2)
        window.toggle_archive_chat(first_chat)
        self.assertTrue(self.store.meta_map()[first_chat]["archived"])
        window._set_status_filter("archived")
        archived_ids = [
            window.history.item(i).data(ui.Qt.ItemDataRole.UserRole)[0]
            for i in range(window.history.count())
            if len(window.history.item(i).data(ui.Qt.ItemDataRole.UserRole)) == 4
        ]
        self.assertEqual(archived_ids, [first_chat])
