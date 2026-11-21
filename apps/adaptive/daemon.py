#!/usr/bin/python3
"""Coordinate UPower and the Debian power-profiles-daemon on a private bus connection."""
import json
import logging
import os
import signal
import socket
import time
import xml.etree.ElementTree as ET

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

from policy import Policy, battery, thresholds
from status import CONFIG, RUN, STATE, atomic

PP = "org.freedesktop.UPower.PowerProfiles"
PP_PATH = "/org/freedesktop/UPower/PowerProfiles"
UP = "org.freedesktop.UPower"
UP_PATH = "/org/freedesktop/UPower"
SD = "org.freedesktop.systemd1"
SD_PATH = "/org/freedesktop/systemd1"
PROPS = "org.freedesktop.DBus.Properties"
APP = "org.kernova.Adaptive"
CONFLICTS = ("tlp", "tuned", "auto-cpufreq", "system76-power")


class Service:
    def __init__(self):
        self.bus = dbus.SystemBus(private=True)
        self.loop = GLib.MainLoop()
        self.owner = self.up = self.timer = self.suspended = None
        self.manager = self.interface(SD, SD_PATH, SD + ".Manager")
        self.minimum_stamp = 0
        self.last_status = {}
        self.delay = 1
        self.retry = None
        settings = json.loads(STATE.read_text()) if STATE.exists() else {"enabled": False, "override": False}
        if any(type(settings.get(k)) is not bool for k in ("enabled", "override")):
            raise ValueError("invalid persistent automation settings")
        self.policy = Policy(self.hold, self.release, self.save, **settings)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        control = RUN / "control"
        control.unlink(missing_ok=True)
        self.sock.bind(str(control))
        os.chmod(control, 0o600)
        GLib.io_add_watch(self.sock.fileno(), GLib.IO_IN, self.command)
        self.bus.add_signal_receiver(self.names, "NameOwnerChanged", "org.freedesktop.DBus",
                                     bus_name="org.freedesktop.DBus")
        for iface in (PP, UP, UP + ".Device", SD + ".Unit"):
            self.bus.add_signal_receiver(self.properties, "PropertiesChanged", PROPS,
                                         arg0=iface, sender_keyword="sender", path_keyword="path")
        self.bus.add_signal_receiver(self.revoked, "ProfileReleased", PP, path=PP_PATH, sender_keyword="sender")
        self.bus.add_signal_receiver(self.sleep, "PrepareForSleep", "org.freedesktop.login1.Manager",
                                     bus_name="org.freedesktop.login1")
        self.bus.call_on_disconnection(lambda bus: self.loop.quit())
        self.manager.Subscribe(timeout=3)
        self.sd = self.bus.get_name_owner(SD)
        self.refresh()
        address = os.environ.get("NOTIFY_SOCKET")
        if address:
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as notify:
                notify.sendto(b"READY=1", address.replace("@", "\0", 1) if address.startswith("@") else address)
        GLib.timeout_add_seconds(60, self.watchdog)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self.stop)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self.stop)

    def interface(self, dest, path, iface):
        return dbus.Interface(self.bus.get_object(dest, path, introspect=False), iface)

    def props(self, dest, path, iface):
        return self.interface(dest, path, PROPS).GetAll(iface, timeout=3)

    def save(self, enabled, override):
        atomic(STATE, {"enabled": enabled, "override": override})

    def command(self, fd, condition):
        data, address = self.sock.recvfrom(32)
        try:
            if data not in (b"on", b"off"):
                raise ValueError("unknown command")
            self.policy.configure(data == b"on")
            self.refresh()
            response = b"ok"
        except (OSError, ValueError, dbus.DBusException) as exc:
            response = str(exc).encode()[:512]
        try:
            self.sock.sendto(response, address)
        except OSError:
            pass
        return True

    def hold(self):
        return int(self.backend.HoldProfile("power-saver", "Low system battery", APP, timeout=5))

    def release(self, cookie):
        try:
            self.backend.ReleaseProfile(dbus.UInt32(cookie), timeout=5)
        except dbus.DBusException:
            # Dropping our private connection also removes any surviving hold.
            self.loop.quit()
            GLib.idle_add(self.stop)
            raise

    def names(self, name, old, new):
        if name == PP:
            if old == self.owner:
                self.policy.reset_owner()
                self.owner = None
            self.queue()
        elif name in (UP, SD):
            if name == UP:
                self.up = None
            self.queue()

    def properties(self, iface, changes, invalid, sender, path):
        if sender == self.owner and iface == PP and path == PP_PATH:
            if "ActiveProfile" in changes:
                holds = changes.get("ActiveProfileHolds")
                ours = None if holds is None else any(h.get("ApplicationId") == APP for h in holds)
                self.policy.changed(str(changes["ActiveProfile"]), ours)
            self.queue()
        elif sender == self.up or (sender == self.sd and path.rsplit("/", 1)[-1] in
                                    ("tlp_2eservice", "tuned_2eservice", "auto_2dcpufreq_2eservice",
                                     "system76_2dpower_2eservice")):
            self.queue()

    def revoked(self, cookie, sender):
        if sender == self.owner:
            self.policy.released(int(cookie))
            self.queue()

    def sleep(self, sleeping):
        self.suspended = bool(sleeping)
        if not sleeping:
            self.minimum_stamp = int(time.time())
        self.refresh()

    def queue(self):
        if self.timer is None:
            self.timer = GLib.timeout_add(350, self.queued)

    def queued(self):
        self.timer = None
        self.refresh()
        return False

    def watchdog(self):
        self.refresh()
        return True

    def inputs(self, status):
        self.up = self.bus.get_name_owner(UP)
        root = self.props(self.up, UP_PATH, UP)
        if "OnBattery" in root:
            status["on_battery"] = bool(root["OnBattery"])
        db = self.interface(self.up, UP_PATH, UP)
        device = self.props(self.up, db.GetDisplayDevice(timeout=3), UP + ".Device")
        aggregate = device.get("IsPresent") and device.get("Type") == 2
        if not aggregate:
            devices = [self.props(self.up, path, UP + ".Device") for path in db.EnumerateDevices(timeout=3)]
            batteries = [v for v in devices if v.get("Type") == 2 and v.get("IsPresent") and v.get("PowerSupply")]
            if len(batteries) != 1:
                raise ValueError("no unambiguous system battery")
            device = batteries[0]
        if device.get("UpdateTime", 0) < self.minimum_stamp:
            raise ValueError("waiting for post-resume UPower sample")
        return battery(root, device, time.time(), aggregate)

    def provider(self, status):
        owner = self.bus.get_name_owner(PP)
        if owner != self.owner:
            self.policy.reset_owner()
            self.owner = owner
        pid = self.interface("org.freedesktop.DBus", "/org/freedesktop/DBus",
                             "org.freedesktop.DBus").GetConnectionUnixProcessID(owner, timeout=3)
        unit = self.manager.GetUnitByPID(dbus.UInt32(pid), timeout=3)
        provider = str(self.props(SD, unit, SD + ".Unit")["Id"])
        status["backend"] = provider
        if provider != "power-profiles-daemon.service":
            raise ValueError("unsupported D-Bus provider: " + provider)
        for name in CONFLICTS:
            try:
                unit = self.manager.GetUnit(name + ".service", timeout=3)
            except dbus.DBusException as exc:
                if exc.get_dbus_name() == SD + ".NoSuchUnit":
                    continue
                raise
            if self.props(SD, unit, SD + ".Unit")["ActiveState"] not in ("inactive", "failed"):
                raise ValueError("active policy conflict: " + name)
        props = self.props(owner, PP_PATH, PP)
        status["profiles"] = [str(v["Profile"]) for v in props["Profiles"]]
        status["effective_profile"] = str(props["ActiveProfile"])
        if self.policy.effective is None:
            self.policy.effective = status["effective_profile"]
        if getattr(self, "validated", None) != owner:
            xml = self.interface(owner, PP_PATH, "org.freedesktop.DBus.Introspectable").Introspect(timeout=3)
            api = ET.fromstring(xml).find(f"interface[@name='{PP}']")
            if api is None or any(api.find(f"{kind}[@name='{name}']") is None for kind, name in
                                  (("method", "HoldProfile"), ("method", "ReleaseProfile"), ("signal", "ProfileReleased"))):
                raise ValueError("temporary hold API unavailable")
            if str(props.get("Version", "")).split(".")[:2] != ["0", "30"]:
                raise ValueError("provider version outside validated 0.30 series")
            self.validated = owner
        self.backend = self.interface(owner, PP_PATH, PP)
        if "power-saver" not in status["profiles"]:
            raise ValueError("power-saver profile unavailable")
        status["capabilities"] = ["HoldProfile", "ReleaseProfile", "ProfileReleased"]
        holds = props["ActiveProfileHolds"]
        return bool(holds) and (self.policy.cookie is None or len(holds) > 1 or
                                holds[0].get("ApplicationId") != APP)

    def refresh(self):
        p = self.policy
        s = dict(backend=None, capabilities=[], profiles=[], effective_profile=None, on_battery=None,
                 percentage=None, enter_threshold=None, exit_threshold=None)
        reasons = []
        competing = False
        try:
            settings = json.loads(CONFIG.read_text())
            limits = thresholds(settings["enter_threshold"], settings["exit_threshold"])
            s["enter_threshold"], s["exit_threshold"] = limits
        except (ValueError, OSError, KeyError, TypeError) as exc:
            limits = None
            reasons.append("configuration: " + str(exc))
        try:
            if self.suspended:
                raise ValueError("suspended")
            s["on_battery"], s["percentage"] = self.inputs(s)
        except (dbus.DBusException, ValueError, KeyError, TypeError) as exc:
            reasons.append("battery: " + str(exc))
        try:
            competing = self.provider(s)
        except (dbus.DBusException, ValueError, KeyError) as exc:
            reasons.append("backend: " + str(exc))
        try:
            p.evaluate(s["on_battery"], s["percentage"], limits, "; ".join(reasons), competing)
        except dbus.DBusException as exc:
            p.denied = str(exc)
            p.state, p.reason = "UNAVAILABLE", p.denied
            if exc.get_dbus_name() in ("org.freedesktop.DBus.Error.NoReply",
                                       "org.freedesktop.DBus.Error.Disconnected",
                                       "org.freedesktop.DBus.Error.Timeout"):
                # An ambiguous method reply can leave an unknown hold. Disconnect this client.
                self.loop.quit()
                GLib.idle_add(self.stop)
        s.update(enabled=p.enabled, external_override=p.override, state=p.state, reason=p.reason,
                 unavailable_reasons=reasons + ([p.denied] if p.denied else []),
                 requested_profile="power-saver" if p.cookie is not None else None, owns_hold=p.cookie is not None)
        if s != self.last_status:
            if (s["state"], s["reason"]) != (self.last_status.get("state"), self.last_status.get("reason")):
                logging.warning("%s: %s", s["state"], s["reason"])
            atomic(RUN / "status.json", s)
            self.last_status = s
        if reasons and self.retry is None:
            self.retry = GLib.timeout_add_seconds(self.delay, self.reconnect)
            self.delay = min(60, self.delay * 2)
        elif not reasons:
            self.delay = 1

    def reconnect(self):
        self.retry = None
        self.refresh()
        return False

    def stop(self):
        self.loop.quit()
        return False

    def run(self):
        try:
            self.loop.run()
        finally:
            try:
                self.policy.drop()
            finally:
                self.bus.close()
                self.sock.close()


if __name__ == "__main__":
    DBusGMainLoop(set_as_default=True)
    Service().run()
