"""Offline diagnostics, privacy boundaries and the confirmation-to-write sequence."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/adaptive"))
import doctor

PIPEWIRE = "ActiveState=active\nInvocationID=" + "f" * 32


def sink_info(serial=101):
    return (f'id 42, type PipeWire:Interface:Node\n    object.serial = "{serial}"\n'
            '  * media.class = "Audio/Sink"\n    node.name = "private-device-name"')


def fs(blocks=60, inodes=70, total=100):
    return SimpleNamespace(f_blocks=100, f_bavail=blocks, f_files=total, f_favail=inodes, f_frsize=4096)


class DoctorTests(unittest.TestCase):
    def cli(self, *argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = doctor.main(argv)
        return code, output.getvalue()

    def test_full_scan_only_reads_local_allowlisted_state(self):
        read_commands = {
            ("systemctl", "--user", "show", "pipewire.service", "-p", "ActiveState", "-p", "InvocationID"): PIPEWIRE,
            ("nmcli", "-t", "-f", "STATE", "general"): "connected (site only)",
            ("wpctl", "inspect", "@DEFAULT_AUDIO_SINK@"): sink_info(),
            ("wpctl", "get-volume", "42"): "Volume: 0.17 [MUTED]",
            ("dpkg-query", "-W", "-f=${db:Status-Status}", "kernova-performance"): "installed",
            ("dpkg", "--audit"): "",
            ("systemctl", "show", "kernova-adaptive.service", "-p", "ActiveState", "--value"): "active",
        }
        flags = ("apt-cache", "-o", "Dir::Cache::pkgcache=", "-o", "Dir::Cache::srcpkgcache=")
        read_commands[(*flags, "policy", "kernova-performance")] = "kernova-performance:\n  Installed: 0.1.18\n  Candidate: 0.1.19"
        read_commands[(*flags, "madison", "kernova-performance")] = "kernova-performance | 0.1.19 | https://private-token@host/"
        state = dict(state="EXTERNAL_OVERRIDE", enabled=True, external_override=True, reason="private-debug-text")
        psi = {k: {"some": {"total": 25}} for k in ("cpu", "memory", "io")}
        with (patch.object(doctor, "command", side_effect=lambda *a, **kw: read_commands[a]),
              patch.object(doctor, "pressure", return_value=psi), patch.object(doctor, "read_status", return_value=state),
              patch.object(doctor.os, "statvfs", create=True, return_value=fs()), patch.object(doctor, "platform_issue", return_value=None)):
            code, report = self.cli("scan", "--json")
        self.assertEqual(code, 1)
        data = json.loads(report)
        self.assertEqual(data["schema_version"], 1)
        rows = {r["id"]: r for r in data["checks"]}
        self.assertEqual(set(rows), set(doctor.CHECKS) - {"network.online"})
        self.assertNotIn("private-", report)
        for key, row in rows.items():
            self.assertTrue(all(row[k] for k in ("evidence", "explanation", "next_step")))
            self.assertEqual(row["status"], "PROBLEM" if key == "audio.mute" else "OK")
            self.assertEqual(row["fix_id"], "audio.unmute" if key == "audio.mute" else None)

    def test_offline_and_online_timeout_are_independent(self):
        with (patch.object(doctor, "platform_issue", return_value=None),
              patch.object(subprocess, "run", side_effect=[
                  subprocess.CompletedProcess([], 0, "connected (local only)", ""),
                  subprocess.TimeoutExpired(["curl"], 5)]) as run):
            code, report = self.cli("check", "network", "--online", "--json")
        self.assertEqual(code, 2)
        local, online = json.loads(report)["checks"]
        self.assertEqual((local["status"], online["status"]), ("OK", "UNKNOWN"))
        self.assertIn("timed out", online["evidence"])
        self.assertEqual(run.call_args.kwargs["timeout"], 5)
        self.assertIn("--max-time", run.call_args.args[0])
        with patch.object(doctor, "command", return_value="disconnected"):
            self.assertEqual(doctor.check("network.local").status, "PROBLEM")

    def test_missing_tools_permissions_or_data(self):
        for error in (FileNotFoundError(), PermissionError(), subprocess.TimeoutExpired(["wpctl"], 5)):
            with self.subTest(error=error), patch.object(subprocess, "run", side_effect=error):
                row = doctor.check("audio.mute")
                self.assertEqual((row.status, row.fix_id), ("UNKNOWN", None))
        with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "permission denied private-token")):
            row = doctor.check("updates.dpkg")
            self.assertEqual(row.status, "UNKNOWN")
            self.assertNotIn("private-token", row.evidence)
        with patch.object(doctor, "command", side_effect=[PIPEWIRE, sink_info(), "Volume unavailable"]):
            self.assertEqual(doctor.check("audio.mute").status, "UNKNOWN")
        with patch.object(doctor, "pressure", return_value=dict(cpu=None, memory=None, io=None)):
            self.assertEqual(doctor.check("adaptive.pressure").status, "UNKNOWN")

    def test_unsupported_platform_performs_no_probes(self):
        with patch.object(doctor.sys, "platform", "win32"), patch.object(doctor, "command") as run:
            _, report = self.cli("scan", "--json")
            self.assertTrue(all(r["status"] == "NOT_APPLICABLE" for r in json.loads(report)["checks"]))
            self.assertNotEqual(self.cli("fix", "audio.unmute")[0], 0)
            run.assert_not_called()

    def test_package_issues_and_no_cached_source(self):
        for replies in (["half-installed"], ["installed", "private package audit details"]):
            with patch.object(doctor, "command", side_effect=replies):
                self.assertEqual(doctor.check("updates.dpkg").status, "PROBLEM")
        with patch.object(doctor, "command", side_effect=["pkg:\n  Installed: 1\n  Candidate: 1", ""]):
            self.assertEqual(doctor.check("updates.candidate").status, "UNKNOWN")

    def test_disk_space_and_inode_exhaustion_are_independent(self):
        for counters, expected in ((fs(0), ("PROBLEM", "OK")), (fs(inodes=1), ("OK", "PROBLEM")),
                                   (fs(inodes=0, total=0), ("OK", "NOT_APPLICABLE"))):
            with patch.object(doctor.os, "statvfs", create=True, return_value=counters):
                self.assertEqual(tuple(doctor.check(k).status for k in ("disk.space", "disk.inodes")), expected)

    def test_unavailable_engine_and_absent_battery(self):
        with patch.object(doctor, "command", return_value="active"):
            for reasons, expected in ((["battery: no present system battery"], "NOT_APPLICABLE"),
                                      (["battery: no present system battery", "backend: denied"], "UNKNOWN"),
                                      (["configuration: invalid thresholds"], "PROBLEM"),
                                      (["configuration: cannot load saved automation settings"], "PROBLEM")):
                with patch.object(doctor, "read_status", return_value=dict(state="UNAVAILABLE", enabled=False,
                                  external_override=False, unavailable_reasons=reasons)):
                    self.assertEqual(doctor.check("adaptive.policy").status, expected)
            with patch.object(doctor, "read_status", side_effect=PermissionError()):
                self.assertEqual(doctor.check("adaptive.policy").status, "UNKNOWN")

    def test_repair_confirmation_races_failure_and_success(self):
        a, b = doctor.Sink(42, 101, "first"), doctor.Sink(42, 102, "first")
        for answer, reads, failure, write, success in (
            ("no", [(a, True)], False, False, False),
            ("yes", [(a, False)], False, False, False),
            ("yes", [(a, True), (a, False)], False, False, False),
            ("yes", [(a, True), (b, True)], False, False, False),
            ("yes", [(a, True), (doctor.Sink(42, 101, "restarted"), True)], False, False, False),
            ("yes", [(a, True), (a, True), (a, True)], True, True, False),
            ("yes", [(a, True), (a, True), (a, False)], True, True, True),
            ("yes", [(a, True), (a, True), (a, True)], False, True, False),
            ("yes", [(a, True), (a, True), (b, False)], False, True, False),
            ("yes", [(a, True), (a, True), (a, False)], False, True, True)):
            with (self.subTest(answer=answer, reads=reads, failure=failure), patch.object(doctor, "platform_issue", return_value=None),
                  patch.object(doctor, "audio_state", side_effect=reads), patch("builtins.input", return_value=answer),
                  patch.object(doctor, "command", side_effect=doctor.Unavailable("denied") if failure else None) as cmd):
                code, output = self.cli("fix", "audio.unmute")
                self.assertEqual(success, code == 0)
                self.assertIn("#42", output)
                if write:
                    cmd.assert_called_once_with("wpctl", "set-mute", "42", "0")
                else:
                    cmd.assert_not_called()

    def test_output_replaced_during_read(self):
        with patch.object(doctor, "command", side_effect=[PIPEWIRE, sink_info(), "Volume: 0.23 [MUTED]", PIPEWIRE, sink_info(102)]):
            self.assertEqual(doctor.check("audio.mute").status, "UNKNOWN")
