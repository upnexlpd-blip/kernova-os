// Disposable-session observer. Only uniquely named QA clients can be modified.
const names = ["One","Two","Three","Fixed"];
function find(name) {
    return workspace.windowList().find(w => w.caption === "WT-QA-" + name);
}
function box(r) { return [r.x,r.y,r.width,r.height]; }
function action(name, fn) { registerShortcut("wtqa." + name, "WT QA " + name,"",fn); }
for (const name of names) action(name, () => {
    const w = find(name);
    if (w) workspace.activeWindow = w;
});
action("Move",() => {
    const w = find("One");
    if (w) w.frameGeometry = {x:48,y:54,width:270,height:220};
});
action("Close",() => { const w = find("Fixed"); if (w) w.closeWindow(); });
action("CloseTwo",() => { const w = find("Two"); if (w) w.closeWindow(); });
action("Untile",() => { const w = find("One"); if (w) w.tile = null; });
action("Maximize",() => find("One").setMaximize(true,true));
action("Restore",() => find("One").setMaximize(false,false));
action("Reset",() => names.forEach((name,i) => {
    const w = find(name);
    if (w && name !== "Fixed") {
        const a = workspace.clientArea(KWin.MaximizeArea,w);
        w.frameGeometry = {x:a.x+20+i*35,y:a.y+25+i*30,width:280,height:210};
    }
}));
action("Snap",() => {
    const frames = {};
    names.forEach(name => {
        const w = find(name);
        if (w) frames[name] = {box:box(w.frameGeometry), area:box(workspace.clientArea(KWin.MaximizeArea,w)),
            max:w.maximizeMode, tile:!!w.tile, resize:w.resizeable, active:w.active, min:[w.minSize.width,w.minSize.height],
            maxSize:[w.maxSize.width,w.maxSize.height],client:box(w.clientGeometry),modal:w.modal,transient:w.transient};
    });
    callDBus("org.kernova.WindowToolsQA","/QA","org.kernova.WindowToolsQA","Snapshot",JSON.stringify(frames));
});
