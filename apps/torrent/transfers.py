"""Per-user BitTorrent session and durable queue."""
import os
from pathlib import Path
import sqlite3
import time

import libtorrent as lt
from queue_state import has_pending, queue_path


def parse_source(source):
    if isinstance(source, str):
        if not source.lower().startswith("magnet:?"):
            raise ValueError("Choose a .torrent file or paste a magnet link.")
        params = lt.parse_magnet_uri(source)
    else:
        params = lt.add_torrent_params()
        params.ti = lt.torrent_info(source)
    return params


def identity(params):
    hashes = params.ti.info_hashes() if params.ti else params.info_hashes
    if hashes.has_v1():
        return str(hashes.v1)
    if hashes.has_v2():
        return str(hashes.v2)
    raise ValueError("The torrent has no info hash.")


class Transfers:
    def __init__(self):
        path = queue_path()
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS transfers (
                id TEXT PRIMARY KEY, source BLOB NOT NULL, folder TEXT NOT NULL,
                paused INTEGER DEFAULT 0, complete INTEGER DEFAULT 0, resume BLOB);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value INTEGER);
        """)
        self.session = None
        self.handles = {}
        self.save_requests = {}
        self.errors = {}

    def start(self):
        if self.session is not None:
            return
        self.session = lt.session({
            "user_agent": "KERNOVA Torrent/0.1.7",
            "listen_interfaces": "0.0.0.0:0,[::]:0",
            "alert_mask": int(lt.alert.category_t.storage_notification |
                              lt.alert.category_t.status_notification |
                              lt.alert.category_t.error_notification),
            "download_rate_limit": self.limit() * 1024,
        })
        for row in self.rows():
            try:
                self.attach(row)
            except (ValueError, RuntimeError, OSError) as exc:
                self.errors[row["id"]] = str(exc)

    def rows(self):
        return self.db.execute("SELECT id, folder, paused, complete FROM transfers ORDER BY rowid").fetchall()

    def pending(self):
        return has_pending(self.db)

    def attach(self, row):
        item = self.db.execute("SELECT source,resume FROM transfers WHERE id=?", (row["id"],)).fetchone()
        params = None
        if item["resume"]:
            try:
                params = lt.read_resume_data(item["resume"])
            except RuntimeError:
                pass
        if params is None:
            params = parse_source(item["source"])
        params.save_path = row["folder"]
        # Keep explicit user pauses independent of libtorrent's queue management.
        params.flags &= ~(lt.torrent_flags.paused | lt.torrent_flags.auto_managed)
        if row["paused"]:
            params.flags |= lt.torrent_flags.paused
        handle = self.session.add_torrent(params)
        self.handles[row["id"]] = handle
        self.errors.pop(row["id"], None)

    def add(self, source, folder):
        params = parse_source(source)
        key = identity(params)
        if self.db.execute("SELECT 1 FROM transfers WHERE id=?", (key,)).fetchone():
            return key
        folder = Path(folder).resolve(strict=True)
        if not folder.is_dir() or not os.access(folder, os.W_OK):
            raise ValueError("Choose a writable download folder.")
        with self.db:
            self.db.execute("INSERT INTO transfers(id,source,folder) VALUES (?,?,?)", (key, source, str(folder)))
            self.attach({"id": key, "folder": str(folder), "paused": False})
        return key

    def pause(self, key, paused):
        with self.db:
            self.db.execute("UPDATE transfers SET paused=? WHERE id=?", (paused, key))
        handle = self.handles.get(key)
        if handle is None:
            self.attach(self.db.execute("SELECT * FROM transfers WHERE id=?", (key,)).fetchone())
        elif paused:
            handle.pause()
            self.request_save(handle)
        else:
            handle.clear_error()
            handle.resume()

    def remove(self, key):
        with self.db:
            self.db.execute("DELETE FROM transfers WHERE id=?", (key,))
        handle = self.handles.pop(key, None)
        if handle is not None:
            self.session.remove_torrent(handle)
            self.save_requests.pop(handle, None)
        self.errors.pop(key, None)

    def limit(self):
        row = self.db.execute("SELECT value FROM settings WHERE key='limit'").fetchone()
        return row[0] if row else 0

    def set_limit(self, value):
        self.session.apply_settings({"download_rate_limit": value * 1024})
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES ('limit',?)", (value,))

    def request_save(self, handle, changed_only=False):
        flags = lt.save_resume_flags_t.save_info_dict
        if changed_only:
            flags |= lt.save_resume_flags_t.only_if_modified
        handle.save_resume_data(flags)
        self.save_requests[handle] = self.save_requests.get(handle, 0) + 1

    def collect(self):
        keys = None
        updates = []
        for alert in self.session.pop_alerts():
            if isinstance(alert, (lt.save_resume_data_alert, lt.save_resume_data_failed_alert,
                                  lt.torrent_finished_alert, lt.metadata_received_alert)):
                if keys is None:
                    keys = {handle: key for key, handle in self.handles.items()}
                key = keys.get(alert.handle)
                if key is None:
                    continue
                if isinstance(alert, lt.save_resume_data_alert):
                    updates.append((lt.write_resume_data_buf(alert.params), key))
                elif not isinstance(alert, lt.save_resume_data_failed_alert):
                    self.request_save(alert.handle)
                    continue
                remaining = self.save_requests.get(alert.handle, 0) - 1
                if remaining > 0:
                    self.save_requests[alert.handle] = remaining
                else:
                    self.save_requests.pop(alert.handle, None)
        if updates:
            with self.db:
                self.db.executemany("UPDATE transfers SET resume=? WHERE id=?", updates)

    def checkpoint(self, changed_only=True):
        for handle in self.handles.values():
            self.request_save(handle, changed_only)

    def close(self):
        if self.session:
            self.collect()
            self.session.pause()
            self.checkpoint(changed_only=False)
            deadline = time.monotonic() + 3
            while self.save_requests and time.monotonic() < deadline:
                self.session.wait_for_alert(100)
                self.collect()
        self.db.close()
