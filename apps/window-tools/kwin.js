let selection = [];
let operation = null;
function area(output) {
    return copyRect(workspace.clientArea(KWin.MaximizeArea, output, workspace.currentDesktop));
}
function tolerance(output) {
    // At 125%, integer Wayland client sizes and physical decoration edges
    // can produce a 1.2 logical pixel discrepancy in the resulting frame.
    return output && !Number.isInteger(output.devicePixelRatio) ? 2 : 1;
}
function feedback(message) {
    callDBus("org.kde.plasmashell", "/org/kde/osdService", "org.kde.osdService",
        "showText", "preferences-system-windows", message);
}
function problem(w) {
    if (!w || w.deleted || !w.managed || !w.normalWindow || w.specialWindow || w.transient || w.modal ||
        String(w.resourceClass).toLowerCase().indexOf("kscreenlocker") >= 0)
        return "Select an ordinary application window.";
    if (w.fullScreen || w.maximizeMode !== 0 || w.tile || w.minimized || w.shade)
        return "Restore the window from fullscreen, maximize, tile, shade or minimize first.";
    if (w.move || w.resize || !w.moveable || !w.resizeable) return "This window must be movable and resizable.";
    if ((!w.onAllDesktops && w.desktops.indexOf(workspace.currentDesktop) < 0) ||
        (w.activities.length && w.activities.indexOf(workspace.currentActivity) < 0))
        return "The selection includes a window on another desktop or activity.";
    if (!w.output || workspace.screens.indexOf(w.output) < 0) return "The window's output is unavailable.";
    return "";
}
function checkedSelection() {
    if (!selection.length) throw Error("Add windows in slot order first.");
    selection.forEach(w => { const why = problem(w); if (why) throw Error(why); });
    return selection.slice();
}
function uniqueOutput(name) {
    const outputs = workspace.screens.filter(o => o.name === name);
    if (outputs.length !== 1) throw Error("Reconnect the saved output or save a new template on the current outputs.");
    return outputs[0];
}
function setting(key, fallback, min, max) {
    const n = Number(readConfig(key, fallback));
    return Number.isInteger(n) && n >= min && n <= max ? n : fallback;
}
const actions = [
    ["Add","Add window to selection"], ["Remove","Remove window from selection"],
    ["Clear","Clear selection"], ["Inspect","Show selection order"],
    ["Side","Side by Side"], ["Coding","Coding layout"], ["Undo","Undo last layout"],
    ["Save","Save selection to template"], ["Load","Apply template"], ["List","List saved templates"],
    ["Delete","Delete template"], ["Reload","Reload saved settings"]
];
const templateBus = "org.kernova.WindowTemplates";
const tilers = ["krohnkite","bismuth","polonium","karousel","kwin-tiling"];
let pending = null;
const deadline = new QTimer();
deadline.singleShot = true;
deadline.interval = 3500;
deadline.timeout.connect(() => {
    pending = null;
    feedback("Window Tools timed out waiting for a session service. Check the selection or template before retrying.");
});
function finish(token) {
    if (pending === token) { deadline.stop(); pending = null; }
}
options.configChanged.connect(() => {
    if (pending && pending.reload) {
        finish(pending);
        feedback("Gap " + setting("Gap",8,0,64) + " logical pixels. Template " + configuredSlot() + ".");
    }
});
function invoke(id, w, slot) {
    if (operation || pending) return feedback("A Window Tools action is in progress.");
    const token = {desktop:workspace.currentDesktop, activity:workspace.currentActivity};
    pending = token;
    deadline.start();
    function safe(fn) {
        return value => {
            if (pending !== token) return;
            try {
                if (token.desktop !== workspace.currentDesktop || token.activity !== workspace.currentActivity)
                    throw Error("The desktop or activity changed. Repeat the action.");
                fn(value);
            } catch (e) { finish(token); feedback(e.message); }
        };
    }
    function done(message) { finish(token); if (message) feedback(message); }
    function execute() {
        if (id === "Reload") {
            token.reload = true;
            callDBus("org.kde.KWin","/KWin","org.kde.KWin","reconfigure");
            return;
        }
        if (id === "Clear") { selection = []; return done("Selection cleared."); }
        if (id === "Inspect") {
            const escaped = value => String(value).slice(0,55).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
            return done(selection.map((item,i) => (i+1) + ". " + escaped(item.caption)).join("\n") || "Selection empty.");
        }
        if (id === "Remove") {
            const at = selection.indexOf(w);
            if (at < 0) throw Error("This window is outside the selection.");
            selection.splice(at,1);
            return done("Removed slot " + (at+1) + ".");
        }
        if (id === "Add") {
            const why = problem(w);
            if (why) throw Error(why);
            const at = selection.indexOf(w);
            if (at >= 0) return done("Already selected in slot " + (at+1) + ".");
            if (selection.length >= 8) throw Error("Select up to eight windows.");
            selection.push(w);
            return done("Added window in slot " + selection.length + ".");
        }
        if (id === "Undo") { done(); return undo(); }
        if (id === "Side" || id === "Coding") {
            const windows = checkedSelection();
            const output = windows[0].output;
            const boxes = preset(id, windows.length, area(output), setting("Gap",8,0,64));
            done();
            return startLayout(windows, windows.map(() => output), boxes);
        }
        const args = [templateBus, "/Templates", templateBus, id];
        if (id !== "List") args.push(String(slot));
        const windows = id === "Save" || id === "Load" ? checkedSelection() : [];
        if (id === "Save") args.push(JSON.stringify({version:1, slots:windows.map(item => ({
            output:uniqueOutput(item.output.name).name, edges:normalize(item.frameGeometry,area(item.output),tolerance(item.output))
        }))}));
        args.push(safe(raw => {
            const reply = JSON.parse(raw);
            if (!reply.ok) throw Error(reply.error);
            if (id === "Load") {
                const slots = reply.value.slots;
                if (slots.length !== windows.length) throw Error("Template " + slot + " needs " + slots.length + " selected windows.");
                if (windows.some((item,i) => !item || item !== selection[i])) throw Error("Selection changed. Select the windows again.");
                const outputs = slots.map(item => uniqueOutput(item.output));
                const boxes = slots.map((item,i) => project(item.edges,area(outputs[i])));
                done();
                startLayout(windows,outputs,boxes);
            } else if (id === "List") done("Saved template slots: " + (reply.value.join(", ") || "none"));
            else done("Template " + slot + (id === "Delete" ? " deleted." : " saved."));
        }));
        callDBus.apply(null,args);
    }
    // Query only on explicit invocation. Choosing windows is also disabled
    // while a known automatic tiler owns placement.
    let remaining = tilers.length + 2;
    function ready() { if (--remaining === 0) execute(); }
    // A running KWin can outlive dpkg removal. The session bus tracks the
    // package-owned service file, independently of an already running helper.
    callDBus("org.freedesktop.DBus","/org/freedesktop/DBus","org.freedesktop.DBus",
        "ListActivatableNames", safe(names => {
            if (names.indexOf(templateBus) < 0) {
                callDBus("org.kde.KWin","/Scripting","org.kde.kwin.Scripting","unloadScript","org.kernova.windowtools");
                throw Error("Window Tools was removed. Reinstall the package to use it.");
            }
            ready();
        }));
    callDBus("org.freedesktop.ScreenSaver","/ScreenSaver","org.freedesktop.ScreenSaver","GetActive",
        safe(locked => { if (locked) { finish(token); return; } ready(); }));
    for (const name of tilers) {
        callDBus("org.kde.KWin","/Scripting","org.kde.kwin.Scripting","isScriptLoaded", name,
            safe(loaded => {
                if (loaded) throw Error("Active tiling script: " + name + ". Choose one in KWin Scripts.");
                ready();
            }));
    }
}
function configuredSlot() { return setting("TemplateSlot",1,1,8); }
for (const action of actions) {
    registerShortcut("org.kernova.windowtools." + action[0], "KERNOVA Window Tools: " + action[1],
        "", () => invoke(action[0], workspace.activeWindow, configuredSlot()));
}
registerUserActionsMenu(w => {
    const slot = configuredSlot();
    return {text:"KERNOVA Window Tools", items:actions.map(action => ({
        text:action[1] + (["Save","Load","Delete"].indexOf(action[0]) >= 0 ? " " + slot : ""),
        triggered:() => invoke(action[0],w,slot)
    }))};
});
