"""On-demand local session service. No window identifiers cross the bus."""
import json
import os
from pathlib import Path

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
from store import Store

BUS = "org.kernova.WindowTemplates"


class Templates(dbus.service.Object):
    def result(self, fn, *args):
        if self.timeout:
            GLib.source_remove(self.timeout)
        self.timeout = GLib.timeout_add_seconds(30, self.loop.quit)
        try:
            return json.dumps({"ok": True, "value": fn(*args)})
        except (ValueError, OSError, RecursionError) as exc:
            return json.dumps({"ok": False, "error": str(exc)[:240]})

    @dbus.service.method(BUS, in_signature="ss", out_signature="s")
    def Save(self, slot, raw):
        return self.result(self.store.save, slot, raw)

    @dbus.service.method(BUS, in_signature="s", out_signature="s")
    def Load(self, slot):
        return self.result(self.store.load, slot)

    @dbus.service.method(BUS, in_signature="s", out_signature="s")
    def Delete(self, slot):
        return self.result(self.store.delete, slot)

    @dbus.service.method(BUS, in_signature="", out_signature="s")
    def List(self):
        return self.result(self.store.list)


if __name__ == "__main__":
    DBusGMainLoop(set_as_default=True)
    name = dbus.service.BusName(BUS, dbus.SessionBus(), do_not_queue=True)
    service = Templates(name, "/Templates")
    base = Path(os.environ.get("XDG_DATA_HOME", ""))
    service.store = Store((base if base.is_absolute() else Path.home() / ".local/share") / "kernova/window-tools")
    service.loop = GLib.MainLoop()
    service.timeout = GLib.timeout_add_seconds(30, service.loop.quit)
    service.loop.run()
