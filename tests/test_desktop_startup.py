from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch


INTEGRATION = Path(__file__).resolve().parents[1] / "apps/integration"


class DesktopStartupTests(unittest.TestCase):
    def test_catalog_hook_launches_only_for_missing_setup_steps(self):
        shell = shutil.which("bash") or r"C:\Program Files\Git\bin\bash.exe"
        hook = (INTEGRATION / "kernova-app-catalog.sh").read_text()
        for xdg in ("", "custom state"):
            with self.subTest(xdg=xdg), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                (directory / "initialize").write_text('echo "$@" >> calls\n', newline="\n")
                # Run the actual hook and timeout with an isolated catalog helper.
                (directory / "hook").write_text(
                    hook.replace("/usr/bin/kernova-get-apps", "/bin/sh ./initialize"), newline="\n")
                state = directory / (xdg or ".local/state") / "kernova"
                state.mkdir(parents=True)

                def login():
                    setup = 'HOME="$PWD"; XDG_STATE_HOME=${1:+"$PWD/$1"}; . ./hook'
                    subprocess.run([shell, "-c", setup, "login", xdg], cwd=directory, check=True)

                login()
                (state / "flathub-initialized").touch()
                login()
                (state / "viber-xcb-initialized").touch()
                login()
                self.assertEqual((directory / "calls").read_text().splitlines(), ["--initialize", "--initialize"])

    def test_weather_panel_loads_database_only_for_saved_cities(self):
        bindings = MagicMock()
        locations = bindings.Gio.Settings.new.return_value.get_value.return_value
        world = bindings.GWeather.Location.get_world
        with patch.dict(sys.modules, {"gi": MagicMock(), "gi.repository": bindings}):
            selected_city = runpy.run_path(str(INTEGRATION / "kernova-weather-panel"))["selected_city"]
            locations.n_children.return_value = 0
            self.assertIsNone(selected_city())
            world.assert_not_called()
            locations.n_children.return_value = 2
            city = object()
            world.return_value.deserialize.side_effect = [None, city]
            self.assertIs(selected_city(), city)
            world.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
