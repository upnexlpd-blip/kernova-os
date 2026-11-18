import hashlib
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import installer_archive as archive

installed_packages = runpy.run_path(str(SCRIPTS / "validate-iso"))["installed_packages"]


class InstallerArchiveTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.evidence = Path(folder.name)
        self.manifest = self.evidence / "SHA256SUMS"
        self.rows = "".join(f"{'a' * 64}  ./{name}\n" for name in archive.FILES)
        self.manifest.write_bytes(self.rows.encode())

    def release(self, suite="trixie", section="SHA256"):
        data = self.manifest.read_bytes()
        name = f"{archive.IMAGE_DIR}/SHA256SUMS"
        return (f"Origin: Debian\nCodename: {suite}\n{section}:\n "
                f"{hashlib.sha256(data).hexdigest()} {len(data)} {name}\n")

    def verify(self, release):
        # gpgv's own check is exercised separately with the real archive.
        # Here supply its authenticated cleartext at the requested output path.
        def verified_output(argv, check):
            self.assertTrue(check)
            self.assertEqual(argv[:3], ["gpgv", "--keyring", archive.KEYRING])
            Path(argv[argv.index("--output") + 1]).write_text(release)

        with patch.object(archive.subprocess, "run", verified_output):
            return archive.verified_hashes(self.evidence)

    def test_requires_verified_trixie_sha256_section(self):
        for release in (self.release(suite="forky"), self.release(section="MD5Sum")):
            with self.subTest(release=release), self.assertRaises(ValueError):
                self.verify(release)

    def test_rejects_modified_manifest(self):
        release = self.release()
        self.manifest.write_bytes(self.rows.replace("a", "b", 1).encode())
        with self.assertRaisesRegex(ValueError, "signed Debian Release"):
            self.verify(release)

    def test_verifies_all_four_paths(self):
        self.assertEqual(self.verify(self.release()), {name: "a" * 64 for name in archive.FILES})

    def test_rejects_missing_or_duplicate_installer(self):
        lines = self.rows.splitlines(keepends=True)
        for rows in (lines[1:], lines + lines[:1]):
            with self.subTest(rows=rows):
                self.manifest.write_bytes("".join(rows).encode())
                with self.assertRaises(ValueError):
                    self.verify(self.release())


class RootFilesystemTests(unittest.TestCase):
    def test_excludes_residual_config_and_reads_multiline_dependencies(self):
        status = ("Package: gone\nStatus: deinstall ok config-files\nVersion: 4\n\n"
                  "Package: desktop\nStatus: install ok installed\nVersion: 1:0.1-1\n"
                  "Depends: app-a (= 1.4),\n app-b | app-c\n")
        packages = installed_packages(status)
        self.assertEqual(set(packages), {"desktop"})
        self.assertEqual(packages["desktop"]["Version"], "1:0.1-1")
        self.assertEqual(packages["desktop"]["Depends"], "app-a (= 1.4), app-b | app-c")
