"""Check Discover routes and first-login Flatpak source ownership."""
from configparser import ConfigParser
from pathlib import Path
import os
import runpy
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "apps/integration/kernova-get-apps"
DESCRIPTOR = ROOT / "packages/defaults/flathub.flatpakrepo"


class DiscoverTests(unittest.TestCase):
    def test_menu_actions_open_their_discover_listings(self):
        launcher = runpy.run_path(str(LAUNCHER))
        menu = ConfigParser()
        menu.read(LAUNCHER.with_suffix(".desktop"), encoding="utf-8")
        with tempfile.TemporaryDirectory() as state:
            marker = Path(state) / "kernova/flathub-initialized"
            marker.parent.mkdir()
            marker.touch()
            with patch.dict(os.environ, XDG_STATE_HOME=state), patch.dict(sys.modules, fcntl=MagicMock()):
                for app, app_id in launcher["APPLICATIONS"].items():
                    with self.subTest(app=app), patch.object(sys, "argv", [str(LAUNCHER), app]), patch("os.execv") as execute:
                        action = next(section for section in menu if section.lower() == "desktop action " + app)
                        self.assertEqual(menu[action]["Exec"], "/usr/bin/kernova-get-apps " + app)
                        launcher["main"]()
                        execute.assert_called_once_with("/usr/bin/plasma-discover", [
                            "/usr/bin/plasma-discover", "--application", "appstream:" + app_id])
                with patch.object(sys, "argv", [str(LAUNCHER)]), patch("os.execv") as execute:
                    launcher["main"]()
                    execute.assert_called_once_with("/usr/bin/plasma-discover", ["/usr/bin/plasma-discover"])

    def test_remote_setup_retries_failures_and_preserves_user_removal(self):
        initialize = runpy.run_path(str(LAUNCHER))["initialize_catalog"]
        bindings = MagicMock()
        installation = bindings.Flatpak.Installation.new_user.return_value
        installation.list_remotes.return_value = []
        installation.add_remote.side_effect = [RuntimeError("simulated failure"), True]
        with tempfile.TemporaryDirectory() as state, patch.dict(os.environ, XDG_STATE_HOME=state), patch.dict(
                sys.modules, {"gi": MagicMock(), "gi.repository": bindings, "fcntl": MagicMock()}):
            with self.assertRaisesRegex(RuntimeError, "simulated failure"):
                initialize(DESCRIPTOR)
            initialize(DESCRIPTOR)
            initialize(DESCRIPTOR)
            self.assertEqual(installation.add_remote.call_count, 2)
            bindings.Flatpak.Remote.new_from_file.return_value.set_gpg_verify.assert_called_with(True)
            bindings.GLib.Bytes.new.assert_called_with(DESCRIPTOR.read_bytes())
