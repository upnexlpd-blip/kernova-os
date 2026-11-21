// At most eight windows have listeners. A committed entry loses ownership
// permanently on subsequent geometry or context changes, even if moved back.
let history = [];
const verifier = new QTimer();
verifier.interval = 80;
function unregister(entry) {
    for (const link of entry.links) { try { link[0].disconnect(link[1]); } catch (_) {} }
    entry.links = [];
}
function retire() {
    history.forEach(unregister);
    history = [];
}
function watch(entry) {
    function connect(signal, fn) {
        signal.connect(fn);
        entry.links.push([signal, fn]);
    }
    const invalidate = () => { entry.lost = true; };
    const w = entry.w;
    for (const sig of [w.interactiveMoveResizeStarted, w.maximizedChanged, w.tileChanged,
        w.desktopsChanged, w.activitiesChanged, w.fullScreenChanged, w.minimizedChanged, w.shadeChanged]) {
        connect(sig, invalidate);
    }
    connect(w.frameGeometryChanged, () => {
        if (entry.applied && !operation) {
            if (!closeRect(w.frameGeometry, entry.applied, 0.001)) invalidate();
        } else if (entry.reached && !closeRect(w.frameGeometry, entry.expected, tolerance(w.output))) invalidate();
    });
}
function contextOK(e) {
    return !e.lost && e.w && !e.w.deleted && e.desktop === workspace.currentDesktop &&
        e.activity === workspace.currentActivity && [e.from, e.to].every(site =>
            workspace.screens.indexOf(site.output) >= 0 && closeRect(area(site.output), site.area));
}
function matches(e, site, box) {
    return contextOK(e) && !problem(e.w) && e.w.output === site.output && closeRect(e.w.frameGeometry, box,tolerance(site.output));
}
function makeEntry(w, output, target) {
    const why = problem(w);
    if (why) throw Error(why);
    const before = copyRect(w.frameGeometry);
    const from = {output:w.output, area:area(w.output)};
    const to = {output, area:area(output)};
    checkLocation(from.output, before, tolerance(from.output));
    checkFit(w, output, target);
    return {w, from, to, before, target, desktop:workspace.currentDesktop,
        activity:workspace.currentActivity, expected:target, reached:false, lost:false, links:[]};
}
function checkLocation(output, target, rounding) {
    if (!inside(target, area(output),rounding)) throw Error("Place the whole frame inside its output work area.");
    const cx = target.x + target.width / 2;
    const cy = target.y + target.height / 2;
    const owners = workspace.screens.filter(o => {
        const g = o.geometry;
        return cx >= g.x && cx < g.x + g.width && cy >= g.y && cy < g.y + g.height;
    });
    if (owners.length !== 1 || owners[0] !== output)
        throw Error("Separate overlapping outputs in Display Configuration before placing this frame.");
}
function checkFit(w, output, target, rounding = 0) {
    checkLocation(output, target, rounding);
    if (w.output !== output && !w.moveableAcrossScreens) throw Error("A window cannot move between these outputs.");
    const width = target.width - (w.frameGeometry.width - w.clientGeometry.width);
    const height = target.height - (w.frameGeometry.height - w.clientGeometry.height);
    if (width < w.minSize.width || height < w.minSize.height ||
        width > w.maxSize.width || height > w.maxSize.height) throw Error("A selected window's size limits do not fit this layout.");
}
function startLayout(windows, outputs, boxes) {
    const entries = windows.map((w,i) => {
        try {
            const entry = makeEntry(w, outputs[i], boxes[i]);
            entry.slot = i + 1;
            return entry;
        } catch (error) { throw Error("Slot " + (i + 1) + ": " + error.message); }
    });
    const changed = entries.filter(e => !matches(e,e.to,e.target));
    if (!changed.length) return feedback("Already arranged. Previous Undo retained.");
    retire();
    history = changed;
    history.forEach(watch);
    requestFrames("apply", changed, changed.length);
}
function requestFrames(mode, entries, total) {
    operation = {mode, entries, total, ticks:0, stable:0};
    for (const e of entries) {
        e.reached = false;
        e.expected = mode === "apply" ? e.target : e.before;
        try {
            if (contextOK(e)) {
                e.w.frameGeometry = copyRect(e.expected);
                e.reached = matches(e, mode === "apply" ? e.to : e.from, e.expected);
            }
        } catch (_) { e.lost = true; }
    }
    verifier.start();
}
function restorable(e) {
    if (!matches(e, e.to, e.applied || e.target)) return false;
    try { checkFit(e.w,e.from.output,e.before,tolerance(e.from.output)); } catch (_) { return false; }
    return true;
}
function undo() {
    if (!history.length) return feedback("No layout to undo in this session.");
    const entries = history.filter(restorable);
    if (!entries.length) {
        const count = history.length;
        retire();
        return feedback("Undo restored 0 of " + count + ". Windows or their work areas changed.");
    }
    requestFrames("undo", entries, history.length);
}
verifier.timeout.connect(() => {
    const op = operation;
    if (!op) return;
    const applying = op.mode === "apply";
    const arrived = op.entries.filter(e => matches(e, applying ? e.to : e.from, e.expected));
    arrived.forEach(e => { e.reached = true; });
    op.stable = arrived.length === op.entries.length ? op.stable + 1 : 0;
    if (++op.ticks < 18 && op.stable < 2) return;
    verifier.stop();
    operation = null;
    if (applying && op.stable >= 2) {
        for (const e of arrived) e.applied = copyRect(e.w.frameGeometry);
        return feedback("Layout applied to " + arrived.length + " changed windows.");
    }
    if (applying) {
        const owned = arrived.filter(restorable);
        if (owned.length) return requestFrames("rollback", owned, op.total);
        retire();
        return feedback("Layout incomplete. 0 of " + op.total + " changes verified for rollback. Inspect the windows.");
    }
    const restored = arrived.length;
    const count = op.total;
    const skipped = history.filter(e => arrived.indexOf(e) < 0).map(e => {
        if (!e.w || e.w.deleted) return e.slot + " (closed)";
        if (!contextOK(e)) return e.slot + " (window or work area changed)";
        return e.slot + " (geometry changed or refused)";
    });
    retire();
    feedback((op.mode === "undo" ? "Undo" : "Incomplete layout. Rollback") + " restored " +
        restored + " of " + count + " requested frames." + (skipped.length ? " Check slots: " + skipped.join(", ") : ""));
});
workspace.windowRemoved.connect(w => {
    selection = selection.filter(item => item !== w);
    for (const e of history) if (e.w === w) { e.lost = true; unregister(e); e.w = null; }
});
function invalidateContext() { for (const e of history) if (!contextOK(e)) e.lost = true; }
workspace.screensChanged.connect(invalidateContext);
workspace.currentDesktopChanged.connect(invalidateContext);
workspace.currentActivityChanged.connect(invalidateContext);
