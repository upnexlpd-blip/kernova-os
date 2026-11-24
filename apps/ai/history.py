"""Per-account chat history. Only the desktop thread owns this connection."""

import os
from pathlib import Path
import sqlite3
import time


class ChatRemoved(RuntimeError):
    """Another window removed the conversation this window was displaying."""


class History:
    def __init__(self, directory=None):
        if directory:
            directory = Path(directory)
        elif os.environ.get("XDG_DATA_HOME"):
            directory = Path(os.environ["XDG_DATA_HOME"]) / "kernova-ai"
        elif os.name == "nt" and os.environ.get("LOCALAPPDATA"):
            directory = Path(os.environ["LOCALAPPDATA"]) / "kernova-ai"
        else:
            directory = Path.home() / ".local/share/kernova-ai"
        if os.name == "nt":
            try:
                directory.mkdir(parents=True, exist_ok=True)
                file = directory / "history.sqlite3"
                fd = os.open(file, os.O_CREAT | os.O_RDWR)
                os.close(fd)
            except PermissionError:
                fallback = Path(__file__).resolve().parents[2] / "build" / "kernova-ai-data"
                fallback.mkdir(parents=True, exist_ok=True)
                file = fallback / "history.sqlite3"
        else:
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            file = directory / "history.sqlite3"
            # Restrict the database even when XDG_DATA_HOME has a permissive umask.
            fd = os.open(file, os.O_CREAT | os.O_RDWR, 0o600)
            os.close(fd)
        self.db = sqlite3.connect(file)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA secure_delete=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY, title TEXT NOT NULL,
                mode TEXT NOT NULL, model TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY, chat INTEGER NOT NULL REFERENCES chats ON DELETE CASCADE,
                role TEXT NOT NULL, content TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS chat_messages ON messages(chat, id);
            CREATE TABLE IF NOT EXISTS chat_sequence (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1), last_id INTEGER NOT NULL
            );
            INSERT OR IGNORE INTO chat_sequence
                SELECT 1, COALESCE(MAX(id), 0) FROM chats;
            CREATE TABLE IF NOT EXISTS chat_meta (
                chat INTEGER PRIMARY KEY REFERENCES chats ON DELETE CASCADE,
                project TEXT NOT NULL DEFAULT '',
                updated_at INTEGER NOT NULL DEFAULT 0,
                pinned INTEGER NOT NULL DEFAULT 0,
                unread INTEGER NOT NULL DEFAULT 0,
                archived INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS turn_meta (
                chat INTEGER NOT NULL REFERENCES chats ON DELETE CASCADE,
                msg_index INTEGER NOT NULL,
                label TEXT NOT NULL,
                elapsed REAL NOT NULL,
                PRIMARY KEY (chat, msg_index)
            );
        """)
        existing_cols = {row[1] for row in self.db.execute("PRAGMA table_info(chat_meta)").fetchall()}
        for col, spec in (
            ("updated_at", "INTEGER NOT NULL DEFAULT 0"),
            ("pinned", "INTEGER NOT NULL DEFAULT 0"),
            ("unread", "INTEGER NOT NULL DEFAULT 0"),
            ("archived", "INTEGER NOT NULL DEFAULT 0"),
        ):
            if col not in existing_cols:
                self.db.execute(f"ALTER TABLE chat_meta ADD COLUMN {col} {spec}")
        self.db.commit()

    def list(self):
        return self.db.execute("""
            SELECT c.id, c.title, c.mode, c.model FROM chats c
            LEFT JOIN chat_meta cm ON cm.chat = c.id
            ORDER BY COALESCE(cm.pinned, 0) DESC,
                     (SELECT MAX(m.id) FROM messages m WHERE m.chat=c.id) DESC,
                     c.id DESC
        """).fetchall()

    def meta_map(self):
        rows = self.db.execute(
            "SELECT chat, project, updated_at, pinned, unread, archived FROM chat_meta"
        ).fetchall()
        return {
            cid: dict(project=proj, updated_at=ts, pinned=bool(pin), unread=bool(unr), archived=bool(arc))
            for cid, proj, ts, pin, unr, arc in rows
        }

    def _ensure_meta(self, chat):
        self.db.execute("""
            INSERT INTO chat_meta(chat, updated_at) SELECT id, ? FROM chats WHERE id=?
            ON CONFLICT(chat) DO NOTHING
        """, (int(time.time()), chat))

    def project_for(self, chat):
        if chat is None:
            return ""
        row = self.db.execute("SELECT project FROM chat_meta WHERE chat=?", (chat,)).fetchone()
        return row[0] if row else ""

    def set_project(self, chat, project):
        if chat is not None:
            with self.db:
                self._ensure_meta(chat)
                self.db.execute("UPDATE chat_meta SET project=? WHERE chat=?", (project or "", chat))

    def rename(self, chat, title):
        cleaned = " ".join(str(title).split())[:72]
        if not cleaned:
            return
        with self.db:
            if not self.db.execute("UPDATE chats SET title=? WHERE id=?", (cleaned, chat)).rowcount:
                raise ChatRemoved()

    def set_flag(self, chat, column, enabled):
        if column not in ("pinned", "unread", "archived"):
            raise ValueError("Unsupported flag.")
        with self.db:
            self._ensure_meta(chat)
            if not self.db.execute(f"UPDATE chat_meta SET {column}=? WHERE chat=?",
                                   (1 if enabled else 0, chat)).rowcount:
                raise ChatRemoved()

    def duplicate(self, chat):
        rows = self.db.execute("SELECT title, mode, model FROM chats WHERE id=?", (chat,)).fetchone()
        if not rows:
            raise ChatRemoved()
        title, mode, model = rows
        msgs = self.messages(chat)
        proj = self.project_for(chat)
        now = int(time.time())
        with self.db:
            new_id = self.db.execute("UPDATE chat_sequence SET last_id=last_id+1 RETURNING last_id").fetchone()[0]
            self.db.execute("INSERT INTO chats(id,title,mode,model) VALUES(?,?,?,?)",
                            (new_id, (title[:64] + " (copy)"), mode, model))
            self.db.execute("INSERT INTO chat_meta(chat, project, updated_at) VALUES(?, ?, ?)",
                            (new_id, proj, now))
            for msg in msgs:
                self.db.execute("INSERT INTO messages(chat,role,content) VALUES(?,?,?)",
                                (new_id, msg["role"], msg["content"]))
        return new_id

    def turn_details(self, chat):
        if chat is None:
            return {}
        rows = self.db.execute("SELECT msg_index, label, elapsed FROM turn_meta WHERE chat=?", (chat,)).fetchall()
        return {index: (step_label, elapsed) for index, step_label, elapsed in rows}

    def save_turn_detail(self, chat, msg_index, step_label, elapsed):
        if chat is not None:
            with self.db:
                self.db.execute("""
                    INSERT INTO turn_meta(chat, msg_index, label, elapsed)
                    SELECT id, ?, ?, ? FROM chats WHERE id=?
                    ON CONFLICT(chat, msg_index) DO UPDATE SET label=excluded.label, elapsed=excluded.elapsed
                """, (int(msg_index), str(step_label)[:160], max(0.0, float(elapsed)), chat))

    def messages(self, chat):
        if chat is None:
            return []
        rows = self.db.execute("""
            SELECT m.role, m.content FROM chats c LEFT JOIN messages m ON m.chat=c.id
            WHERE c.id=? ORDER BY m.id
        """, (chat,)).fetchall()
        if not rows:
            raise ChatRemoved()
        return [dict(role=r, content=c) for r, c in rows if r is not None]

    def send(self, chat, mode, model, prompt, project=""):
        now = int(time.time())
        with self.db:
            if chat is None:
                title = " ".join(prompt.split())[:72]
                # Keep IDs stable even after deleting every chat in an existing database.
                chat = self.db.execute("UPDATE chat_sequence SET last_id=last_id+1 RETURNING last_id").fetchone()[0]
                self.db.execute("INSERT INTO chats(id,title,mode,model) VALUES(?,?,?,?)",
                                (chat, title, mode, model))
            else:
                if not self.db.execute("UPDATE chats SET mode=?, model=? WHERE id=?",
                                       (mode, model, chat)).rowcount:
                    raise ChatRemoved()
            if project:
                self.db.execute("""
                    INSERT INTO chat_meta(chat, project, updated_at, unread) VALUES(?, ?, ?, 0)
                    ON CONFLICT(chat) DO UPDATE SET project=excluded.project, updated_at=excluded.updated_at, unread=0
                """, (chat, project, now))
            else:
                self.db.execute("""
                    INSERT INTO chat_meta(chat, updated_at, unread) VALUES(?, ?, 0)
                    ON CONFLICT(chat) DO UPDATE SET updated_at=excluded.updated_at, unread=0
                """, (chat, now))
            self.db.execute("INSERT INTO messages(chat,role,content) VALUES(?, 'user', ?)",
                            (chat, prompt))
        return chat

    def append(self, chat, role, content):
        now = int(time.time())
        with self.db:
            if not self.db.execute("INSERT INTO messages(chat,role,content) SELECT id,?,? FROM chats WHERE id=?",
                                   (role, content, chat)).rowcount:
                raise ChatRemoved()
            self.db.execute("""
                INSERT INTO chat_meta(chat, updated_at) SELECT id, ? FROM chats WHERE id=?
                ON CONFLICT(chat) DO UPDATE SET updated_at=excluded.updated_at
            """, (now, chat))

    def delete(self, chat):
        with self.db:
            if not self.db.execute("DELETE FROM chats WHERE id=?", (chat,)).rowcount:
                raise ChatRemoved()
