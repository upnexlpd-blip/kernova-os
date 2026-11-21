"""Eight ordered layout templates, independent of KWin and D-Bus."""
import json
import math
import os
from pathlib import Path
import stat
import tempfile

LIMIT = 8192


def validate(raw):
    if len(raw) > LIMIT or len(raw.encode("utf-8")) > LIMIT:
        raise ValueError("Template is too large.")
    data = json.loads(raw)
    if not isinstance(data, dict) or set(data) != {"version", "slots"} or type(data["version"]) is not int or data["version"] != 1:
        raise ValueError("Unsupported template schema.")
    slots = data["slots"]
    if not isinstance(slots, list) or not 1 <= len(slots) <= 8:
        raise ValueError("A template needs one to eight ordered slots.")
    for slot in slots:
        if not isinstance(slot, dict) or set(slot) != {"output", "edges"}:
            raise ValueError("Invalid layout slot.")
        name, edges = slot["output"], slot["edges"]
        if not isinstance(name, str) or not 1 <= len(name) <= 128 or not name.isprintable():
            raise ValueError("Invalid output name.")
        if not isinstance(edges, list) or len(edges) != 4 or not all(
            type(v) in (float, int) and 0 <= v <= 1 and math.isfinite(v) for v in edges
        ) or edges[0] >= edges[2] or edges[1] >= edges[3]:
            raise ValueError("Invalid normalized frame.")
    return data


class Store:
    def __init__(self, root):
        self.root = Path(root)

    def path(self, slot):
        if slot not in tuple(str(n) for n in range(1, 9)):
            raise ValueError("Choose a template slot from 1 to 8.")
        return self.root / (slot + ".json")

    def save(self, slot, raw):
        path = self.path(slot)
        data = validate(raw)
        encoded = json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > LIMIT:
            raise ValueError("Template is too large.")
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, mode="wb") as tmp:
            try:
                tmp.write(encoded)
                tmp.flush()
                os.fsync(tmp.fileno())
                tmp.close()
                os.replace(tmp.name, path)
            finally:
                Path(tmp.name).unlink(missing_ok=True)

    def load(self, slot):
        try:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
            with os.fdopen(os.open(self.path(slot), flags), "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise ValueError("Template slot must be a regular file.")
                raw = stream.read(LIMIT + 1)
        except FileNotFoundError:
            raise ValueError("This template slot is empty.") from None
        if len(raw) > LIMIT:
            raise ValueError("Stored template is too large.")
        return validate(raw.decode("utf-8"))

    def delete(self, slot):
        self.path(slot).unlink(missing_ok=True)

    def list(self):
        return [n for n in range(1, 9) if self.path(str(n)).is_file()]
