"""Exercise the installed adapter against real PPD only in the isolated QEMU guest."""
import sys
import time
from pathlib import Path

sys.path.insert(0, "/usr/share/kernova/adaptive")
from daemon import APP, PP, PP_PATH, PROPS, SD, SD_PATH, DBusGMainLoop, GLib, Service, dbus
from policy import Policy


def until(check):
    context = GLib.MainContext.default()
    for _ in range(100):
        while context.pending():
            context.iteration(False)
        if check():
            return
        time.sleep(.03)
    raise AssertionError("timed out waiting for PPD event")


def main():
    if Path("/sys/class/dmi/id/sys_vendor").read_text().strip() != "QEMU":
        raise SystemExit("requires disposable QEMU hardware")
    DBusGMainLoop(set_as_default=True)
    service = Service.__new__(Service)
    service.bus = dbus.SystemBus(private=True)
    service.bus.set_exit_on_disconnect(False)
    service.manager = service.interface(SD, SD_PATH, SD + ".Manager")
    service.owner = None
    service.queue = lambda: None
    service.policy = Policy(service.hold, service.release, lambda *_: None)
    summary = {}
    assert not service.provider(summary), summary
    print("Actual daemon and capabilities:", summary, flush=True)
    service.bus.add_signal_receiver(service.properties, "PropertiesChanged", PROPS, arg0=PP,
                                    sender_keyword="sender", path_keyword="path")
    service.bus.add_signal_receiver(service.revoked, "ProfileReleased", PP, path=PP_PATH,
                                    sender_keyword="sender")
    p = service.policy
    p.configure(True)
    p.evaluate(True, 19, (20, 25))
    until(lambda: p.effective == "power-saver")
    print("Acquired low-battery hold", flush=True)
    assert p.cookie and not p.override
    p.evaluate(False, 19, (20, 25))
    until(lambda: p.effective == "balanced")
    assert not p.override and p.cookie is None
    print("Confirmed AC release", flush=True)
    p.evaluate(True, 19, (20, 25))
    until(lambda: p.effective == "power-saver")
    observer = dbus.SystemBus(private=True)
    peer = observer.get_object(PP, PP_PATH)
    if sys.argv[-1] == "external":
        dbus.Interface(peer, PROPS).Set(PP, "ActiveProfile", "balanced")
        until(lambda: p.override)
        assert p.cookie is None
    else:
        assert any(h["ApplicationId"] == APP for h in dbus.Interface(peer, PROPS).Get(PP, "ActiveProfileHolds"))
        service.bus.close()
        until(lambda: not dbus.Interface(peer, PROPS).Get(PP, "ActiveProfileHolds"))
    print("Verified actual PPD", sys.argv[-1], flush=True)


if __name__ == "__main__":
    main()
