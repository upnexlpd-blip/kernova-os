import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/performance"))
from profiles import PROFILES


@unittest.skipUnless(sys.platform.startswith("linux"), "Linux process scheduler")
class PerformanceTest(unittest.TestCase):
    def test_each_profile_changes_only_child_process(self):
        import os
        old = (os.nice(0), os.sched_getscheduler(0))
        inspect = ("import json,os; from pathlib import Path; print(json.dumps("
                   "[os.nice(0),os.sched_getscheduler(0),int(Path('/proc/self/timerslack_ns').read_text())]))")
        for key, p in PROFILES.items():
            with self.subTest(profile=key):
                proc = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] /
                                      "apps/performance/profiles.py"), key, "--", sys.executable, "-c", inspect],
                                      capture_output=True, text=True, check=True)
                nice, sched, slack = json.loads(proc.stdout)
                self.assertEqual(nice, min(19, old[0] + p.nice))
                self.assertEqual(sched, os.SCHED_BATCH if p.batch else old[1])
                self.assertEqual(slack, p.slack_ns)
        self.assertEqual((os.nice(0), os.sched_getscheduler(0)), old)
