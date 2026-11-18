"""Behavior of the Linux system probes and fixed launch actions."""

from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


APP = Path(__file__).resolve().parents[1] / "apps" / "welcome"
sys.path.insert(0, str(APP))

from system_info import (  # noqa: E402
    ACTIONS, boot_session, cpu_name, language_for, memory_kib, os_pretty_name,
    pci_gpu_names, string_mapping,
)


class WelcomeProbeTests(unittest.TestCase):
    def test_live_requires_exact_parameter(self):
        self.assertEqual(boot_session("quiet boot=live components"), "live")
        self.assertEqual(boot_session("root=/dev/vda1 quiet"), "installed")
        self.assertEqual(boot_session("log.boot=live boot=live-rescue"), "installed")
        self.assertEqual(boot_session('comment="prefers boot=live"'), "installed")
        for invalid in (None, "", "    ", 'boot="unterminated'):
            self.assertEqual(boot_session(invalid), "unknown")

    def test_os_release_is_parsed_as_data(self):
        self.assertEqual(
            os_pretty_name('NAME=Debian\nPRETTY_NAME="Debian GNU/Linux 13 (trixie)"'),
            "Debian GNU/Linux 13 (trixie)",
        )
        self.assertEqual(os_pretty_name('NAME=Debian\nPRETTY_NAME="unterminated'), "Debian")
        self.assertEqual(os_pretty_name("PRETTY_NAME='$(ignored-command)'"), "$(ignored-command)")
        self.assertIsNone(os_pretty_name("ID=debian"))

    def test_cpu_and_usable_memory(self):
        self.assertEqual(cpu_name("processor: 0\nmodel name\t: Sample x86\n"), "Sample x86")
        self.assertIsNone(cpu_name("processor: 0"))
        self.assertEqual(memory_kib("MemTotal:    8388608 kB\nMemFree: 39213 kB"), 8388608)
        for invalid in ("MemFree: 1024 kB", "MemTotal: 0 kB", "MemTotal: 42 GiB"):
            self.assertIsNone(memory_kib(invalid))

    def test_graphics_reports_names_and_falls_back_to_pci_ids(self):
        with TemporaryDirectory() as directory:
            devices = Path(directory)
            # The probe only matches the folder name, so portable test addresses
            # can stand in for sysfs names containing colons on Windows.
            gpu = devices / "gpu.0"
            gpu.mkdir()
            (gpu / "class").write_text("0x030200\n", encoding="utf-8")
            (gpu / "vendor").write_text("0x1234\n", encoding="utf-8")
            (gpu / "device").write_text("0x5678\n", encoding="utf-8")
            network = devices / "network.0"
            network.mkdir()
            (network / "class").write_text("0x020000\n", encoding="utf-8")
            output = ('gpu.0 "3D controller" "Vendor" "GPU Model"\n'
                      'network.0 "Ethernet controller" "Vendor" "Network Card"')
            with patch("system_info.subprocess.run", return_value=subprocess.CompletedProcess(
                (), 0, stdout=output
            )) as run:
                self.assertEqual(pci_gpu_names(devices), "Vendor GPU Model")
                self.assertEqual(run.call_args.args, (("/usr/bin/lspci", "-D", "-mm"),))
                self.assertEqual(run.call_args.kwargs["timeout"], 2)
                self.assertFalse(run.call_args.kwargs.get("shell", False))
            with patch("system_info.subprocess.run", side_effect=FileNotFoundError):
                self.assertEqual(pci_gpu_names(devices), "PCI 1234:5678")
            with patch("system_info.subprocess.run", side_effect=subprocess.TimeoutExpired((), 2)):
                self.assertEqual(pci_gpu_names(devices), "PCI 1234:5678")
            with patch("system_info.subprocess.run") as run:
                self.assertIsNone(pci_gpu_names(devices / "missing"))
                run.assert_not_called()

    def test_actions_use_fixed_commands_and_require_the_network_module(self):
        for action in ACTIONS.values():
            self.assertTrue(action.arguments[0].startswith("/usr/bin/"))
            self.assertTrue(all(re.fullmatch(r"[A-Za-z0-9/_-]+", arg) for arg in action.arguments))
        network = ACTIONS["network"]
        self.assertEqual(network.arguments, ("/usr/bin/systemsettings", "kcm_networkmanagement"))
        self.assertIsNotNone(network.extra_package)
        _, marker = network.extra_package
        with patch("system_info.os.access", return_value=True), patch.object(
            Path, "is_file", autospec=True, side_effect=lambda path: path != marker
        ):
            self.assertEqual(network.missing_package(), "plasma-nm")
        with patch.object(Path, "is_file", return_value=False):
            self.assertEqual(network.missing_package(), "systemsettings")

    def test_macedonian_locale_and_english_fallback(self):
        for code in ("mk", "mk_MK.UTF-8", "mk-MK", "MK@custom"):
            self.assertEqual(language_for(code), "mk")
        self.assertEqual(language_for("en_US"), "en")
        self.assertEqual(language_for("sr_RS"), "en")
        english = string_mapping(APP / "locales" / "en.json")
        macedonian = string_mapping(APP / "locales" / "mk.json")
        self.assertEqual(english.keys(), macedonian.keys())
        self.assertEqual(macedonian["start"], "Први чекори")
        for key in english:
            self.assertEqual(
                re.findall(r"\{[a-z]+\}", english[key]),
                re.findall(r"\{[a-z]+\}", macedonian[key]),
                key,
            )

    def test_missing_and_malformed_product_metadata(self):
        with TemporaryDirectory() as directory:
            metadata = Path(directory) / "product.json"
            self.assertEqual(string_mapping(metadata), {})
            metadata.write_text("{", encoding="utf-8")
            self.assertEqual(string_mapping(metadata), {})
            metadata.write_text('{"version":"0.1.0", "invalid":100}', encoding="utf-8")
            self.assertEqual(string_mapping(metadata), {"version": "0.1.0"})


if __name__ == "__main__":
    unittest.main()
