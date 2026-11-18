import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

VM = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/vm"))
scope = VM["create"].__globals__


class GuestTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("builtins.print"))
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        settings = patch.dict(scope, ROOT=self.root, DISK_SIZE=4096)
        settings.start()
        self.addCleanup(settings.stop)

    def test_installed_boot_has_only_private_disk(self):
        VM["create"]("installed", "bios")
        iso = self.root / "development,preview.iso"
        iso.write_bytes(b"read-only fixture")
        media = VM["command"]("installed", iso)
        self.assertIn("ide-cd,drive=cd,bootindex=1", media)
        self.assertTrue(any("readonly=on" in s and "development,,preview.iso" in s for s in media))
        detached = VM["command"]("installed", None)
        self.assertFalse(any("cdrom" in s or ".iso" in s for s in detached))
        self.assertTrue(any("format=raw" in s and "disk.raw" in s for s in detached))
        self.assertNotIn("hostfwd", " ".join(detached))

    def test_refuses_reuse_path_traversal_and_foreign_disk(self):
        for bad in ("../escape", "x/y", "/dev/sda", "new,format=raw"):
            with self.assertRaises(ValueError):
                VM["guest_dir"](bad)
        VM["create"]("test", "bios")
        with self.assertRaises(FileExistsError):
            VM["create"]("test", "bios")
        (VM["guest_dir"]("test") / "disk.raw").write_bytes(b"wrong disk")
        with self.assertRaises(ValueError):
            VM["command"]("test", None)

    def test_secure_needs_enrolled_keys(self):
        def descriptor(name, features):
            p = self.root / name
            p.write_text(json.dumps({"interface-types": ["uefi"], "features": features,
                                     "targets": [{"architecture": "x86_64", "machines": ["pc-q35-*"]}],
                                     "mapping": {"device": "flash",
                                                 "executable": {"format": "raw", "filename": "code"},
                                                 "nvram-template": {"format": "raw", "filename": "vars"}}}))
            return p
        blank = descriptor("01.json", ["secure-boot"])
        normal = descriptor("02.json", [])
        with self.assertRaisesRegex(ValueError, "No matching"):
            VM["select_firmware"]([blank, normal], "secure")
        enrolled = descriptor("03.json", ["enrolled-keys", "secure-boot"])
        self.assertEqual(VM["select_firmware"]([blank, normal, enrolled], "secure")[0], enrolled)
        self.assertEqual(VM["select_firmware"]([blank, normal, enrolled], "uefi")[0], normal)
