"""Read the login resume queue before loading GTK or libtorrent."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3


def queue_path():
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    return state / "kernova-torrent" / "queue.sqlite"


def has_pending(db):
    return db.execute("SELECT 1 FROM transfers WHERE NOT paused AND NOT complete LIMIT 1").fetchone() is not None


def resume_needed():
    path = queue_path()
    if not path.is_file():
        return False
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=0)) as db:
            return has_pending(db)
    except sqlite3.Error:
        # Let normal initialization handle an unfinished database or a transient lock.
        return True
