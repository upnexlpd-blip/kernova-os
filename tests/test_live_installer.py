import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "config/profiles/installer"
PAYLOAD = PROFILE / "includes.binary/kernova-installer"
configure = runpy.run_path(str(PAYLOAD / "activate"))["configure"]
environment = runpy.run_path(str(PAYLOAD / "kernova-live-install"))["launch_environment"]


class LiveInstallerTests(unittest.TestCase):
    def test_grub_live_hook_uri_survives_menu_generation(self):
        hook = PROFILE / "hooks/live/0900-kernova-installer.hook.binary"
        uri = "live-config.hooks=file:///run/live/medium/kernova-installer/activate"
        with tempfile.TemporaryDirectory() as tmp:
            menu = Path(tmp) / "boot/grub/grub.cfg"
            menu.parent.mkdir(parents=True)
            entries = f"linux /live/vmlinuz {uri}\nlinux /live/vmlinuz {uri} nomodeset\n"
            menu.write_text(entries.replace("file:///", "file://", 1))
            for _ in range(2):
                subprocess.run([sys.executable, hook], cwd=tmp, check=True)
                self.assertEqual(menu.read_text(), entries)
            menu.write_text(entries.replace(uri, "", 1))
            result = subprocess.run([sys.executable, hook], cwd=tmp, capture_output=True)
            self.assertNotEqual(result.returncode, 0)

    def test_local_display_and_minimal_environment(self):
        for display in ("", "localhost:1", ":1 junk", ":0\n-option"):
            with self.subTest(display=display), self.assertRaises(ValueError):
                environment(display, "/proc/self/fd/3")
        env = environment(":0.0", "/proc/self/fd/3")
        self.assertEqual(set(env), {"DISPLAY", "XAUTHORITY", "HOME", "USER", "LOGNAME", "LANG",
                                    "PATH", "QT_QPA_PLATFORM"})
        self.assertEqual(env["HOME"], "/root")

    def test_installer_opens_without_password_only_for_active_local_live_user(self):
        action = ElementTree.parse(PAYLOAD / "install.policy").find("./action")
        self.assertEqual(action.get("id"), "org.kernova.live.install")
        self.assertTrue(all(e.text == "no" for e in action.findall("./defaults/*")))
        helper = action.find("./annotate[@key='org.freedesktop.policykit.exec.path']").text
        self.assertEqual(helper, "/usr/libexec/kernova-live-install")
        self.assertIn("Exec=/usr/bin/pkexec " + helper + "\n", (PAYLOAD / "install.desktop").read_text("utf-8"))
        rules = (PAYLOAD / "install.rules").read_text()
        for condition in ('action.id === "org.kernova.live.install"', "subject.local", "subject.active",
                          'subject.user === "kernova-live"', "return polkit.Result.YES;"):
            self.assertIn(condition, rules)
        self.assertNotIn("AUTH_", rules)
        self.assertEqual((PROFILE / "includes.binary/live/config.conf.d/kernova-installer.conf").read_text().strip(),
                         'LIVE_HOOKS="file:///run/live/medium/kernova-installer/activate"')
        self.assertFalse((PROFILE / "includes.chroot").exists())

    def test_wizard_choices_and_target_cleanup_survive_reactivation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "etc/apt/sources.list": "deb [trusted=yes] file:/run/live/medium trixie main non-free-firmware\n"
                    "deb https://deb.debian.org/debian trixie main non-free-firmware\n",
                "etc/calamares/settings.conf": "\nbranding: debian\nprompt-install: false\n"
                    "  - dpkg-unsafe-io\n  - sources-media\n  - machineid\n"
                    "  - bootloader-config\n  - grubcfg\n  - dpkg-unsafe-io-undo\n"
                    "  - sources-media-unmount\n  - sources-final\n  - umount\n",
                "etc/calamares/modules/mount.conf": "extraMounts:\n",
                "etc/calamares/modules/bootloader.conf": "installEFIFallback: true\n",
                "etc/calamares/modules/welcome.conf": "requirements:\n  requiredStorage: 15\n",
                "etc/calamares/modules/users.conf": "setRootPassword: false\npasswordRequirements:\n"
                    "    libpwquality:\n        - minlen=0\n        - minclass=0\n",
                "etc/calamares/branding/debian/branding.desc": "",
                "usr/share/kernova/product.json": '{"name":"KERNOVA OS","version":"0.1.0"}',
                "usr/share/icons/hicolor/scalable/apps/kernova-logo.svg": "<svg/>",
                "usr/share/applications/calamares.desktop": "[Desktop Entry]\n",
            }
            for location, contents in files.items():
                path = root / location
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(contents)
            configure(root, PAYLOAD)
            self.assertEqual((root / "etc/apt/sources.list").read_text(),
                             "deb https://deb.debian.org/debian trixie main non-free-firmware\n")
            # calamares-settings-debian diverts the upstream menu entry on a
            # real trixie image. The branded launcher and policy still activate.
            (root / "usr/share/applications/calamares.desktop").unlink()
            (root / "usr/share/polkit-1/actions/org.kernova.live.install.policy").unlink()
            configure(root, PAYLOAD)
            self.assertTrue((root / "usr/share/polkit-1/actions/org.kernova.live.install.policy").is_file())
            cal = root / "etc/calamares"
            self.assertIn("prompt-install: true", (cal / "settings.conf").read_text())
            self.assertNotIn("sources-final", (cal / "settings.conf").read_text())
            self.assertIn("dontChroot: false", (cal / "modules/shellprocess.conf").read_text())
            self.assertIn("device: /run/live/medium", (cal / "modules/mount.conf").read_text())
            self.assertIn("installEFIFallback: false", (cal / "modules/bootloader.conf").read_text())
            partition = (cal / "modules/partition.conf").read_text()
            self.assertIn("initialPartitioningChoice: none", partition)
            self.assertIn("allowManualPartitioning: true", partition)
            users = (cal / "modules/users.conf").read_text()
            self.assertIn("setRootPassword: false", users)
            self.assertEqual(users.count("dictpath=/run/live/medium/kernova-installer/cracklib_dict"), 1)
            self.assertEqual(users.count("doAutologin: false"), 1)
            self.assertIn("forbidden_names: [root, nobody, kernova-live]", users)
            self.assertEqual(json.loads((cal / "branding/kernova/branding.desc").read_text())
                             ["strings"]["shortProductName"], "KERNOVA OS")
            purge = (cal / "modules/packages.conf").read_text().splitlines()
            live = (PROFILE / "package-lists/installer.list.chroot_live").read_text().splitlines()
            for package in ("calamares", "calamares-settings-debian"):
                self.assertIn(package, live)
                self.assertIn("      - " + package, purge)
