"""Adapter failures under Debian's D-Bus bindings without a live battery."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/adaptive"))
try:
    import daemon
except ModuleNotFoundError as exc:
    if exc.name not in ("dbus", "gi"):
        raise
    daemon = None


@unittest.skipUnless(daemon, "requires Debian D-Bus and GLib bindings")
class AdapterTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        paths = patch.multiple(daemon, CONFIG=root/"config", RUN=root, STATE=root/"settings.json")
        paths.start()
        self.addCleanup(paths.stop)
        daemon.CONFIG.write_text('{"enter_threshold":20,"exit_threshold":25}')
        self.s = daemon.Service.__new__(daemon.Service)
        self.s.last_status = {}
        self.s.retry = None
        self.s.delay = 1
        timers = patch.multiple(daemon.GLib, timeout_add_seconds=Mock(return_value=123), source_remove=Mock())
        timers.start()
        self.addCleanup(timers.stop)
        self.s.suspended = False
        self.s.settings_issue = None
        self.s.inputs = Mock(return_value=(True, 11))
        self.s.provider = Mock(return_value=False)
        self.hold = Mock(return_value=17)
        self.release = Mock()
        self.s.policy = daemon.Policy(self.hold, self.release, Mock(), enabled=True)

    def test_invalid_saved_state_preserved_until_explicit_recovery(self):
        s = self.s
        s.hold = self.hold
        for raw in ('{', '[]', 'null', '{"enabled":1,"override":false}',
                    '{"enabled":false,"override":true}', '{"enabled":true,"override":false,"bad":1}'):
            with self.subTest(raw=raw):
                daemon.STATE.write_text(raw)
                s.policy = s.load_policy()
                s.refresh()
                self.assertEqual(daemon.STATE.read_text(), raw)
                self.assertFalse(s.policy.enabled)
                self.assertEqual(s.last_status["state"], "UNAVAILABLE")
                self.assertIn("saved automation settings", s.last_status["reason"])
                self.hold.assert_not_called()
        s.policy.configure(False)
        s.refresh()
        self.assertEqual(s.last_status["state"], "OBSERVE")
        self.assertFalse(s.load_policy().enabled)
        self.assertIsNone(s.settings_issue)
        s.policy.configure(True)
        self.assertTrue(s.load_policy().enabled)

    def test_denied_hold_is_not_retried_until_explicit_enable(self):
        self.hold.side_effect = daemon.dbus.DBusException("permission denied",
                              name="org.freedesktop.DBus.Error.AccessDenied")
        self.s.refresh()
        self.s.refresh()
        self.hold.assert_called_once()
        self.assertEqual(self.s.last_status["state"], "UNAVAILABLE")
        self.assertFalse(self.s.last_status["owns_hold"])
        self.hold.side_effect = None
        self.s.policy.configure(True)
        self.s.refresh()
        self.assertTrue(self.s.last_status["owns_hold"])

    def test_suspend_unavailable_then_fresh(self):
        self.s.refresh()
        self.s.sleep(True)
        self.release.assert_called_once_with(17)
        self.s.inputs.side_effect = ValueError("waiting for post-resume UPower sample")
        self.s.sleep(False)
        self.assertGreater(self.s.minimum_stamp, 0)
        self.hold.assert_called_once()
        self.s.inputs.side_effect = None
        self.s.refresh()
        self.assertEqual(self.hold.call_count, 2)

    def test_active_conflict_or_invalid_config_releases(self):
        self.s.refresh()
        self.s.provider.side_effect = ValueError("active policy conflict: tlp")
        self.s.refresh()
        self.release.assert_called_once_with(17)
        self.assertIn("tlp", self.s.last_status["reason"])
        self.s.provider.side_effect = None
        daemon.CONFIG.write_text('{"enter_threshold":15,"exit_threshold":10}')
        self.s.refresh()
        self.hold.assert_called_once()
        self.assertIn("threshold", self.s.last_status["reason"])

    def test_provider_poll_honors_manual_choice_after_missed_signal(self):
        s = self.s
        del s.provider  # Exercise the real provider reader with a simulated bus.
        s.owner = s.validated = ":1.50"
        s.bus = Mock()
        s.bus.get_name_owner.return_value = s.owner
        s.interface = Mock()
        s.interface.return_value.GetConnectionUnixProcessID.return_value = 100
        s.manager = Mock()
        s.manager.GetUnitByPID.return_value = "/provider"
        s.props = Mock(side_effect=lambda dest, path, iface: (
            {"Id": "power-profiles-daemon.service"} if path == "/provider" else
            {"ActiveState": "inactive"} if iface == daemon.SD + ".Unit" else
            {"ActiveProfile": "balanced", "Profiles": [{"Profile": "power-saver"}], "ActiveProfileHolds": []}))
        s.policy.changed("power-saver", True)
        s.refresh()
        self.assertTrue(s.policy.override)
        s.policy.save.assert_called_once_with(True, True)
        self.hold.assert_not_called()
        self.assertEqual(s.last_status["state"], "EXTERNAL_OVERRIDE")

    def test_watchdog_takes_over_backoff_and_recovery_cancels_pending_retry(self):
        self.s.inputs.side_effect = ValueError("no present system battery")
        self.s.refresh()
        self.s.refresh()
        daemon.GLib.timeout_add_seconds.assert_called_once_with(1, self.s.reconnect)
        self.s.inputs.side_effect = None
        self.s.refresh()
        daemon.GLib.source_remove.assert_called_once_with(123)
        self.assertIsNone(self.s.retry)
        daemon.GLib.timeout_add_seconds.reset_mock()
        self.s.inputs.side_effect = ValueError("no present system battery")
        self.s.refresh()
        for _ in range(6):
            self.s.reconnect()
        self.s.watchdog()
        self.assertEqual([call.args[0] for call in daemon.GLib.timeout_add_seconds.call_args_list],
                         [1, 2, 4, 8, 16, 32])
        self.assertIsNone(self.s.retry)

    def test_partial_profile_notification_waits_for_hold_information(self):
        s = self.s
        s.owner, s.queue = ":1.20", Mock()
        p = s.policy
        p.changed("balanced", False)
        s.refresh()  # acquires cookie 17
        def signal(profile):
            s.properties(daemon.PP, {"ActiveProfile": profile}, [], s.owner, daemon.PP_PATH)
        signal("power-saver")
        self.assertFalse(p.override)
        self.assertEqual(p.cookie, 17)
        p.changed("power-saver", True)  # full provider refresh confirms the hold
        self.assertIsNone(p.expected)
        s.inputs.return_value = (False, 50)
        s.refresh()
        signal("balanced")
        self.assertFalse(p.override)
        p.changed("balanced", False)
        signal("performance")  # an unrelated transition is honored immediately
        self.assertTrue(p.override)
