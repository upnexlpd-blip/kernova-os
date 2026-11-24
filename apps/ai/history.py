"""Per-account chat history. Only the desktop thread owns this connection."""

import os
from pathlib import Path
import sqlite3


class ChatRemoved(RuntimeError):
    """Another window removed the conversation this window was displaying."""


class History:
    def __init__(self, directory=None):
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
        directory = Path(directory) if directory else base / "kernova-ai"
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
        """)

    def list(self):
        return self.db.execute("""
            SELECT c.id, c.title, c.mode, c.model FROM chats c
            ORDER BY (SELECT MAX(m.id) FROM messages m WHERE m.chat=c.id) DESC
        """).fetchall()

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

    def send(self, chat, mode, model, prompt):
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
            self.db.execute("INSERT INTO messages(chat,role,content) VALUES(?, 'user', ?)",
                            (chat, prompt))
        return chat

    def append(self, chat, role, content):
        with self.db:
            if not self.db.execute("INSERT INTO messages(chat,role,content) SELECT id,?,? FROM chats WHERE id=?",
                                   (role, content, chat)).rowcount:
                raise ChatRemoved()

    def delete(self, chat):
        with self.db:
            if not self.db.execute("DELETE FROM chats WHERE id=?", (chat,)).rowcount:
                raise ChatRemoved()
