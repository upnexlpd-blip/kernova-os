"""Run only inside a disposable KERNOVA Plasma session with the package installed."""
import json
import os
import signal
from pathlib import Path
import subprocess
from statistics import median
import time
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

ROOT = Path(__file__).resolve().parent
PLUGIN = "org.kernova.windowtools"
DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
scripting = dbus.Interface(bus.get_object("org.kde.KWin","/Scripting"), "org.kde.kwin.Scripting")
accel = dbus.Interface(bus.get_object("org.kde.kglobalaccel","/component/kwin"), "org.kde.kglobalaccel.Component")
kwin = dbus.Interface(bus.get_object("org.kde.KWin","/KWin"), "org.kde.KWin")
saver = dbus.Interface(bus.get_object("org.freedesktop.ScreenSaver","/ScreenSaver"), "org.freedesktop.ScreenSaver")

class Observer(dbus.service.Object):
    snapshot = None

    @dbus.service.method("org.kernova.WindowToolsQA", in_signature="s", out_signature="")
    def Snapshot(self, data):
        self.snapshot = json.loads(data)

name = dbus.service.BusName("org.kernova.WindowToolsQA",bus)
observer = Observer(name,"/QA")
context = GLib.MainContext.default()

def wait(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        while context.pending():
            context.iteration(False)
        time.sleep(0.012)

def click(name, delay=0.4):
    accel.invokeShortcut(name)
    wait(delay)

def snap():
    observer.snapshot = None
    accel.invokeShortcut("wtqa.Snap")
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        while context.pending():
            context.iteration(False)
        if observer.snapshot is not None:
            return observer.snapshot
        time.sleep(.002)
    raise RuntimeError("KWin probe did not return a snapshot")

def frames():
    return {n:w["box"] for n,w in snap().items() if n != "Fixed"}

def activation(enabled):
    subprocess.run(["kwriteconfig6","--file","kwinrc","--group","Plugins","--key",PLUGIN+"Enabled","true" if enabled else "false"],check=True)
    kwin.reconfigure()
    for _ in range(45):
        wait(.1)
        if bool(scripting.isScriptLoaded(PLUGIN)) == enabled:
            return
    raise RuntimeError("KWin activation failed")

def measure(label):
    pid = int(subprocess.check_output(["pidof","-s","kwin_wayland"]))
    def read():
        stat = Path(f"/proc/{pid}/stat").read_text().rsplit(")",1)[1].split()
        rss = int(next(row.split()[1] for row in Path(f"/proc/{pid}/status").read_text().splitlines() if row.startswith("VmRSS:")))
        return int(stat[11])+int(stat[12]), rss
    wait(2)
    before = read()
    wait(8)
    after = read()
    print("idle",label,"8s CPU ticks",after[0]-before[0],"HZ",os.sysconf("SC_CLK_TCK"),"RSS KiB",before[1],after[1],flush=True)
    timings = []
    for _ in range(7):
        start = time.monotonic()
        snap()
        timings.append((time.monotonic()-start)*1000)
    print("KWin probe round-trip", label, "median ms (7 samples, observer polls)", round(median(timings),1),flush=True)

def act(action, delay=.4):
    click(PLUGIN+"."+action,delay)

def select(*names):
    act("Clear")
    for name in names:
        click("wtqa."+name)
        act("Add")

def near(a,b):
    return all(abs(i-j)<=2 for i,j in zip(a,b))

def check(actual,expected):
    assert actual.keys()==expected.keys() and all(near(actual[n],expected[n]) for n in actual), (actual,expected)

def run():
    activation(False)
    measure("off")
    activation(True)
    measure("on")
    click("wtqa.Reset",1)
    before = frames()
    print("initial",snap(),flush=True)
    assert set(before)=={"One","Two","Three"}
    select("Two","One","Two")
    start = time.monotonic()
    act("Side",0)
    x,y,w,h = snap()["Two"]["area"]
    left = int((w-8)/2+.5)
    side = dict(before, Two=[x,y,left,h],One=[x+left+8,y,w-left-8,h])
    while time.monotonic()-start<3:
        try:
            check(frames(),side)
            break
        except AssertionError:
            wait(.04)
    check(frames(),side)
    print("side-by-side observed ms",round(1000*(time.monotonic()-start)),flush=True)
    wait(.45)
    act("Save")
    act("Undo",.9)
    check(frames(),before)
    act("Load",.9)
    check(frames(),side)
    # The native control is session-scoped; the saved slot must survive reload.
    activation(False)
    activation(True)
    select("Two","One")
    click("wtqa.Reset",.7)
    act("Load",.9)
    check(frames(),side)
    select("One","Three","Two")
    act("Coding",.9)
    col=int((w-8)*.6+.5)
    top=int((h-8)/2+.5)
    coding={"One":[x,y,col,h],"Three":[x+col+8,y,w-col-8,top],"Two":[x+col+8,y+top+8,w-col-8,h-top-8]}
    check(frames(),coding)
    click("wtqa.Move")
    manual=frames()["One"]
    act("Undo",1)
    check(frames(),dict(side,One=manual))
    # One native client withholds its Wayland configure acknowledgement.
    # Xwayland stays responsive and must roll back, without a retry loop.
    click("wtqa.Reset",.7)
    select("One","Three")
    before=frames()
    clients[0].send_signal(signal.SIGSTOP)
    try:
        act("Side",2.3)
        check(frames(),before)
    finally:
        clients[0].send_signal(signal.SIGCONT)
    wait(.6)
    click("wtqa.Reset",.7)
    # Exercise KWin's own maximize and quick-tile actions before our preset.
    for toggle in ["wtqa.Maximize","Window Quick Tile Left"]:
        select("One","Three")
        click("wtqa.One")
        click(toggle,.6)
        for _ in range(20):
            state=snap()["One"]
            if state["max"] or state["tile"]: break
            wait(.1)
        assert state["max"] or state["tile"], (toggle,state)
        before=frames()
        act("Side",.7)
        check(frames(),before)
        if state["max"]:
            click("wtqa.Restore",.6)
        else:
            click("wtqa.Untile",.6)
    select("Fixed","Two")
    before=frames()
    act("Side",.9)
    check(frames(),before)
    select("Three","Two")
    click("wtqa.CloseTwo")
    act("Side",.9)
    assert "Two" not in frames() and near(frames()["Three"],before["Three"])
    activation(False)
    print("PASS: ordered presets, duplicate, both protocols, saved slot reapply, full/partial undo, fixed window, closed slot, KWin reconfigure",flush=True)

if __name__ == "__main__":
    clients=[]
    try:
        if saver.GetActive():
            raise RuntimeError("Unlock the disposable graphical session before starting the test")
        cookie = saver.Inhibit("KERNOVA Window Tools QA","Testing native window placement")
        for backend,names in [("wayland",["One","Two","Fixed"]),("xcb",["Three"])]:
            clients.append(subprocess.Popen(["python3",str(ROOT/"client.py"),*names],env=dict(os.environ,QT_QPA_PLATFORM=backend)))
        wait(2)
        if scripting.isScriptLoaded("wtqa"): scripting.unloadScript("wtqa")
        idx=bus.call_blocking("org.kde.KWin","/Scripting","org.kde.kwin.Scripting",
                              "loadScript","ss",(str(ROOT/"probe.js"),"wtqa"))
        bus.get_object("org.kde.KWin",f"/Scripting/Script{idx}").run(dbus_interface="org.kde.kwin.Script")
        run()
    finally:
        for client in clients: client.terminate()
        if scripting.isScriptLoaded("wtqa"): scripting.unloadScript("wtqa")
