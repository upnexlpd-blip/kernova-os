import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/adaptive"))
from policy import Policy, battery, thresholds
from status import atomic, pressure


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.settings = {}
        self.p = Policy(self.hold, lambda c: self.events.append(("release", c)), self.save)
        self.p.changed("balanced", False)

    def hold(self):
        self.events.append("hold")
        self.p.changed("power-saver", True)  # signal before method reply
        return 71

    def save(self, enabled, override):
        self.settings.update(enabled=enabled, override=override)

    def sample(self, pct, on=True, **kw):
        self.p.evaluate(on, pct, (20, 25), **kw)

    def test_low_and_hysteresis(self):
        self.sample(8)
        self.assertEqual(self.events, [])
        self.p.configure(True)
        for pct in (24, 21):
            self.sample(pct)
        self.assertEqual(self.events, [])
        for pct in (20, 3, 22, 24):
            self.sample(pct)
        self.assertEqual(self.events, ["hold"])
        self.sample(25)
        self.assertEqual(self.events, ["hold", ("release", 71)])

    def test_ac_and_expected_release_signal(self):
        self.p.configure(True)
        self.sample(15)
        self.sample(16, False)
        self.p.released(71)
        self.p.changed("balanced", False)
        self.assertFalse(self.p.override)
        self.assertIsNone(self.p.cookie)

    def test_competitor_and_override(self):
        self.p.configure(True)
        self.sample(10, competing=True)
        self.assertEqual(self.events, [])
        self.sample(10)
        self.p.released(71)
        self.p.changed("performance", False)
        self.sample(9)
        self.assertEqual(self.p.state, "EXTERNAL_OVERRIDE")
        restored = Policy(self.hold, self.fail, self.save, **self.settings)
        restored.evaluate(True, 8, (20, 25))
        self.assertEqual(restored.state, "EXTERNAL_OVERRIDE")
        self.p.configure(True)
        self.sample(9)
        self.assertEqual(self.events.count("hold"), 2)

    def test_external_profile_first(self):
        self.p.configure(True)
        self.sample(11)
        self.p.changed("performance", None)
        self.p.released(71)
        self.assertTrue(self.p.override)
        self.assertEqual(self.events.count(("release", 71)), 1)

    def test_revocation_before_reply(self):
        def revoked():
            self.p.released(19)
            return 19
        self.p.acquire = revoked
        self.p.configure(True)
        self.sample(10)
        self.assertTrue(self.p.override)
        self.assertIsNone(self.p.cookie)

    def test_expected_release_callback_before_reply(self):
        self.p.configure(True)
        self.sample(9)
        self.p.release = self.p.released
        self.sample(26)
        self.assertFalse(self.p.override)

    def test_backend_restart_and_shutdown(self):
        self.p.configure(True)
        self.sample(11)
        self.p.reset_owner()
        self.sample(None, reason="no backend")
        self.assertEqual(self.p.state, "UNAVAILABLE")
        self.assertEqual(self.events, ["hold"])
        self.sample(12)
        self.p.drop()
        self.p.drop()
        self.assertEqual(self.events.count(("release", 71)), 1)

    def test_suspend_and_failure(self):
        self.p.configure(True)
        self.sample(10)
        self.sample(None, reason="suspended")
        self.sample(None, reason="waiting for post-resume sample")
        self.assertEqual(self.events, ["hold", ("release", 71)])
        self.p.denied = "permission denied"
        self.sample(9)
        self.assertEqual(self.p.state, "UNAVAILABLE")
        self.p.configure(True)
        self.sample(9)
        self.p.configure(False)
        self.assertIsNone(self.p.cookie)

    def test_battery_validation(self):
        device = dict(Type=2, IsPresent=True, PowerSupply=True, Percentage=15, UpdateTime=900, State=2)
        root = {"OnBattery": True}
        self.assertEqual(battery(root, device, 1000), (True, 15))
        for key, value in (("UpdateTime", 1), ("UpdateTime", 1001), ("Percentage", float("nan")),
                           ("Type", 5), ("PowerSupply", False), ("State", 1), ("IsPresent", False)):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                battery(root, dict(device, **{key: value}), 1000)

    def test_bad_configuration_and_missing_psi(self):
        for a, b in ((0, 25), (20, 20), (25, 20), (10, 101), (True, 25)):
            with self.assertRaisesRegex(ValueError, "threshold"):
                thresholds(a, b)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            self.assertEqual(pressure(path), dict(cpu=None, memory=None, io=None))
            (path/"cpu").write_text("some avg10=0.12 avg60=0.01 avg300=0.00 total=123\n")
            self.assertEqual(pressure(path)["cpu"]["some"]["total"], 123)
