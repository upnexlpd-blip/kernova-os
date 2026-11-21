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
        paths = patch.multiple(daemon, CONFIG=root/"config", RUN=root)
        paths.start()
        self.addCleanup(paths.stop)
        daemon.CONFIG.write_text('{"enter_threshold":20,"exit_threshold":25}')
        self.s = daemon.Service.__new__(daemon.Service)
        self.s.last_status = {}
        self.s.retry = 1
        self.s.suspended = False
        self.s.inputs = Mock(return_value=(True, 11))
        self.s.provider = Mock(return_value=False)
        self.hold = Mock(return_value=17)
        self.release = Mock()
        self.s.policy = daemon.Policy(self.hold, self.release, Mock(), enabled=True)

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
