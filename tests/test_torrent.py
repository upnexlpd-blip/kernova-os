"""Verify idle login and checkpoint behavior without any external peers."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "apps/torrent"
sys.path.insert(0, str(APP))
from queue_state import queue_path, resume_needed

try:
    from transfers import Transfers, lt
except ImportError:
    lt = None


class QueueTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        state = patch.dict(os.environ, XDG_STATE_HOME=temp.name)
        state.start()
        self.addCleanup(state.stop)

    def test_idle_login_exits_before_desktop_imports_and_database_creation(self):
        def run_autostart():
            subprocess.run([sys.executable, "-E", "-S", "-B", APP / "kernova-torrent", "--resume"],
                           check=True, timeout=5)

        run_autostart()
        self.assertFalse(queue_path().parent.exists())
        queue_path().parent.mkdir()
        with closing(sqlite3.connect(queue_path())) as db:
            db.execute("CREATE TABLE transfers (paused INTEGER, complete INTEGER)")
            db.executemany("INSERT INTO transfers VALUES (?, ?)", [(1, 0), (0, 1)])
            db.commit()
            run_autostart()
            db.execute("INSERT INTO transfers VALUES (0, 0)")
            db.commit()
            self.assertTrue(resume_needed())

    @unittest.skipUnless(lt, "libtorrent is unavailable")
    def test_idle_checkpoints_and_shutdown_with_outstanding_saves(self):
        queue = Transfers()
        self.addCleanup(queue.db.close)
        queue.session = lt.session({
            "listen_interfaces": "127.0.0.1:0", "enable_dht": False, "enable_lsd": False,
            "enable_natpmp": False, "enable_upnp": False,
            "alert_mask": int(lt.alert.category_t.storage_notification | lt.alert.category_t.status_notification |
                              lt.alert.category_t.error_notification),
        })
        for number in range(1, 5):
            key = queue.add(f"magnet:?xt=urn:btih:{number:040x}", self.root)
            queue.pause(key, True)

        def drain():
            end = time.monotonic() + 3
            while queue.save_requests and time.monotonic() < end:
                queue.session.wait_for_alert(100)
                queue.collect()
            self.assertFalse(queue.save_requests)

        drain()
        changes = queue.db.total_changes
        for _ in range(3):
            queue.checkpoint()
            drain()
        self.assertEqual(queue.db.total_changes, changes)
        queue.pause(key, False)
        queue.checkpoint()
        queue.close()
        self.assertFalse(queue.save_requests)
        with closing(sqlite3.connect(queue_path())) as db:
            entries = db.execute("SELECT id, resume FROM transfers").fetchall()
        self.assertEqual(len(entries), 4)
        for key, resume in entries:
            self.assertEqual(str(lt.read_resume_data(resume).info_hashes.v1), key)
