"""Exercise the Performance Center's desktop probes without host package or power changes."""
from gzip import open as gzip_open
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtCore import QSettings, QThreadPool
    from PySide6.QtWidgets import QApplication
except ImportError as exc:
    raise unittest.SkipTest(f"PySide6 is unavailable: {exc}") from exc

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/performance"))
import center


class PerformanceCenterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["performance-test"])

    def test_slow_queries_leave_the_gui_available_and_refresh_only_once(self):
        main_thread = threading.get_ident()
        probe_threads = []
        release = threading.Event()

        def hardware():
            probe_threads.append(threading.get_ident())
            return {"performance"}

        def apt(*args, **kwargs):
            probe_threads.append(threading.get_ident())
            release.wait(2)
            return subprocess.CompletedProcess([], 0, "desktop:\n  Installed: 1\n  Candidate: 2")

        with (tempfile.TemporaryDirectory() as directory,
              patch.object(center, "QSettings", return_value=QSettings(str(Path(directory)/"test.ini"),
                                                                       QSettings.Format.IniFormat)),
              patch.object(center, "power_modes", side_effect=hardware),
              patch.object(center.subprocess, "run", side_effect=apt) as run,
              patch.object(center, "recent_history", return_value="transaction")):
            window = center.Center()
            self.addCleanup(window.close)
            window.tabs.setCurrentIndex(1)
            window.read_updates()
            self.assertFalse(window.refresh.isEnabled())
            release.set()
            self.assertTrue(QThreadPool.globalInstance().waitForDone(3000))
            self.app.processEvents()
            self.assertTrue(window.refresh.isEnabled())
            self.assertEqual(window.hardware, {"performance"})
            self.assertIn("Candidate: 2", window.versions.text())
            self.assertEqual(window.history.toPlainText(), "transaction")
            run.assert_called_once()
            self.assertNotIn(main_thread, probe_threads)

    def test_recent_history_ignores_broken_archive_and_keeps_latest_transactions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current = root / "history.log"
            current.write_text("most recent\n")
            broken = root / "history.log.1.gz"
            broken.write_bytes(b"\x1f\x8b")
            archive = root / "history.log.2.gz"
            with gzip_open(archive, "wt") as log:
                log.write("\n\n".join(f"record {i}" for i in range(100)))
            for i, path in enumerate((archive, broken, current), start=1):
                os.utime(path, (i, i))
            self.assertEqual(center.recent_history(root, 3), "most recent\n\nrecord 99\n\nrecord 98")
