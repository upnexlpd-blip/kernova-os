import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/window-tools"))
from store import Store, validate


class WindowTemplates(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = Store(temp.name)
        self.record = {"version": 1, "slots": [{"output": "DP-1", "edges": [0, 0.1, 1, 0.9]}]}
        self.raw = json.dumps(self.record)

    def test_round_trip_named_slots(self):
        self.store.save("3", self.raw)
        self.assertEqual(self.store.list(), [3])
        self.assertEqual(self.store.load("3"), self.record)
        self.store.delete("3")
        self.store.delete("3")
        with self.assertRaisesRegex(ValueError, "empty"):
            self.store.load("3")

    def test_corrupt_and_bounded(self):
        for raw in ["<", "{}"*6000, self.raw.replace("0.1", "NaN"), self.raw.replace("0.9", "-1"),
                    self.raw.replace('"version": 1', '"version": 2'), self.raw.replace('"output"', '"caption"')]:
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                validate(raw)
        for slot in ["../../oops", "9", "0"]:
            with self.assertRaises(ValueError):
                self.store.save(slot, self.raw)
        self.store.path("1").write_bytes(b"{"*8193)
        with self.assertRaises(ValueError):
            self.store.load("1")

    def test_interrupted_replace_preserves_previous_complete_record(self):
        self.store.save("4", self.raw)
        with patch("store.os.replace", side_effect=OSError("interrupted")), self.assertRaises(OSError):
            self.store.save("4", self.raw.replace("DP-1", "DP-2"))
        self.assertEqual(self.store.load("4"), self.record)
        self.assertEqual(list(self.store.root.iterdir()), [self.store.path("4")])
