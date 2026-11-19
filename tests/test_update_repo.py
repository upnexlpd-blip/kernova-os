"""Exercise release signing and APT enrollment without writing to the host APT configuration."""
from pathlib import Path
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "apps/integration/kernova-update-source"
RELEASE = ROOT / "scripts/build-update-repo"


class RepositoryTests(unittest.TestCase):
    def test_client_rejects_unusable_source_inputs_before_reading_a_key(self):
        source = runpy.run_path(str(CLIENT))["source_text"]
        for url in ("http://localhost", "https://user@localhost", "https://localhost/\nTrusted: yes"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                source(url, Path("unused-key"), "A" * 40)
        with self.assertRaises(ValueError):
            source("https://localhost", Path("unused-key"), "1234")

    @unittest.skipUnless(sys.platform == "linux" and os.getuid() != 0 and all(shutil.which(tool) for tool in
                         ("reprepro", "gpg", "gpgconf", "gpgv", "dpkg-deb", "apt-cache", "apt-get")),
                         "requires an ordinary Debian account with reprepro and GnuPG")
    def test_signed_release_and_isolated_apt_upgrade(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            keys, debs, repo = work / "keys", work / "debs", work / "repo"
            keys.mkdir(mode=0o700)
            debs.mkdir()
            env = dict(os.environ, GNUPGHOME=str(keys), LC_ALL="C")

            def run(*args, **options):
                return subprocess.check_output(args, env=env, cwd=work, text=True, **options)

            try:
                run("gpg", "--batch", "--pinentry-mode", "loopback", "--passphrase", "", "--quick-gen-key",
                    "Temporary release test <test@kernova.invalid>", "ed25519", "sign", "1d")
                listing = run("gpg", "--batch", "--with-colons", "--list-keys")
                fingerprint = next(line.split(":")[9] for line in listing.splitlines() if line.startswith("fpr:"))
                names = (ROOT / "config/profiles/preview.list.chroot").read_text().split()
                for name in names:
                    package = work / name
                    (package / "DEBIAN").mkdir(parents=True)
                    (package / "DEBIAN/control").write_text(
                        f"Package: {name}\nVersion: 1.0\nArchitecture: all\nSection: misc\nPriority: optional\n"
                        "Maintainer: Release Test <test@kernova.invalid>\nDescription: temporary test fixture\n")
                    run("dpkg-deb", "--build", package, debs / f"{name}_1.0_all.deb")
                run(sys.executable, RELEASE, debs, repo, fingerprint)
                key = repo / "kernova-archive-key.asc"
                output = work / "kernova.sources"
                with self.assertRaises(subprocess.CalledProcessError):
                    run(sys.executable, CLIENT, "https://localhost", key, "0" * 40, output)
                self.assertFalse(output.exists())
                run(sys.executable, CLIENT, "https://localhost", key, fingerprint, output)
                output.write_text(output.read_text().replace("https://localhost", repo.as_uri()))
                status = work / "status"
                status.write_text("Package: kernova-desktop\nStatus: install ok installed\nArchitecture: all\n"
                                  "Version: 0.9\nDescription: previous release test fixture\n")
                config = work / "apt.conf"
                config.write_text(
                    f'Dir::Etc::main "/dev/null";\nDir::Etc::parts "-";\nDir::Etc::sourcelist "{output}";\n'
                    f'Dir::Etc::sourceparts "-";\nDir::State "{work}/apt-state";\nDir::State::status "{status}";\n'
                    f'Dir::Cache "{work}/apt-cache";\nDir::Log "{work}/apt-log";\nAPT::Architecture "amd64";\n')
                env["APT_CONFIG"] = str(config)
                (work / "apt-state/lists/partial").mkdir(parents=True)
                (work / "apt-cache/archives/partial").mkdir(parents=True)
                (work / "apt-log").mkdir()
                run("apt-get", "update", "--error-on=any")
                policy = run("apt-cache", "policy", "kernova-desktop")
                self.assertIn("Installed: 0.9", policy)
                self.assertIn("Candidate: 1.0", policy)
                signed = repo / "dists/kernova-trixie/InRelease"
                original = signed.read_bytes()
                self.assertIn(b"Valid-Until:", original)
                signed.write_bytes(original.replace(b"Origin: KERNOVA", b"Origin: altered"))
                with self.assertRaises(subprocess.CalledProcessError):
                    run("apt-get", "update", "--error-on=any")
            finally:
                run("gpgconf", "--kill", "gpg-agent")
