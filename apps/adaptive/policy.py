"""Connection-scoped temporary power policy. No hardware writes outside the adapter."""
import math


def thresholds(enter, exit):
    if not (type(enter) is int and type(exit) is int and 0 < enter < exit <= 100):
        raise ValueError("require integer thresholds 0 < enter_threshold < exit_threshold <= 100")
    return enter, exit


def battery(root, device, now, aggregate=False):
    if device.get("Type") != 2 or not device.get("IsPresent"):
        raise ValueError("no present system battery")
    if not aggregate and not device.get("PowerSupply"):
        raise ValueError("peripheral battery")
    age = now - device.get("UpdateTime", 0)
    pct = float(device.get("Percentage", -1))
    if not 0 <= age <= 600 or not math.isfinite(pct) or not 0 <= pct <= 100:
        raise ValueError("stale or invalid UPower reading")
    on = root.get("OnBattery")
    state = device.get("State")
    if on is None or (on and state not in (2, 3, 6)) or (not on and state not in (1, 4, 5)):
        raise ValueError("unknown or contradictory UPower state")
    return bool(on), pct


class Policy:
    def __init__(self, acquire, release, save, enabled=False, override=False):
        self.acquire, self.release, self.save = acquire, release, save
        self.enabled, self.override = enabled, override
        self.reset_owner()
        self.state, self.reason = "OBSERVE", "starting"

    def reset_owner(self):
        self.cookie = self.expected = self.denied = None
        self.latched = False
        self.effective = self.before = None

    def drop(self):
        if self.cookie is not None:
            cookie = self.cookie
            self.expected = (self.before, False)
            self.release(cookie)
            self.cookie = None

    def external(self):
        if self.enabled and not self.override:
            self.save(self.enabled, True)
            self.override = True
            self.drop()
        self.expected = None

    def changed(self, profile, holds):
        old = self.effective
        self.effective = profile
        if self.expected == (profile, holds):
            self.expected = None
        elif old is not None and profile != old:
            self.external()

    def released(self, cookie):
        if cookie == self.cookie:
            self.cookie = None
            self.external()

    def configure(self, enabled):
        self.save(enabled, False)
        self.enabled, self.override, self.denied = enabled, False, None
        self.latched = False
        if not enabled:
            self.drop()

    def evaluate(self, on, pct, limits, reason=None, competing=False):
        if reason or self.denied:
            self.latched = False
            self.drop()
            self.state, self.reason = "UNAVAILABLE", reason or self.denied
        elif self.override:
            self.state, self.reason = "EXTERNAL_OVERRIDE", "external profile decision; enable explicitly to resume"
        elif not self.enabled:
            self.state, self.reason = "OBSERVE", "automation disabled"
        else:
            enter, exit = limits
            self.latched = on and (pct <= enter or self.latched and pct < exit)
            if not self.latched or competing:
                self.drop()
            elif self.cookie is None:
                self.before = self.effective
                self.expected = ("power-saver", True)
                self.cookie = self.acquire()
            self.state = "AUTO"
            self.reason = ("another client holds a profile" if competing else
                           "low battery" if self.latched else "monitoring power")
