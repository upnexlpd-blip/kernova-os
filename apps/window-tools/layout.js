// Logical frame rectangles. Round shared edges once, keeping output offsets.
function rect(x, y, width, height) { return {x, y, width, height}; }
function copyRect(r) { return rect(r.x, r.y, r.width, r.height); }
function closeRect(a, b, tolerance = 1) {
    return ["x", "y", "width", "height"].every(k => Math.abs(a[k] - b[k]) <= tolerance);
}
function inside(r, a, tolerance = 0) {
    return r.width > 0 && r.height > 0 && r.x >= a.x - tolerance && r.y >= a.y - tolerance &&
        r.x + r.width <= a.x + a.width + tolerance && r.y + r.height <= a.y + a.height + tolerance;
}
function preset(kind, count, a, gap) {
    const coding = kind === "Coding";
    if (count !== (coding ? 3 : 2)) throw Error("Select exactly " + (coding ? 3 : 2) + " windows in slot order.");
    const width = Math.round((a.width - gap) * (coding ? 0.6 : 0.5));
    const right = a.width - gap - width;
    const x = a.x + width + gap;
    const top = Math.round((a.height - gap) / 2);
    const boxes = [rect(a.x, a.y, width, a.height), rect(x, a.y, right, coding ? top : a.height)];
    if (coding) boxes.push(rect(x, a.y + top + gap, right, a.height - gap - top));
    if (!boxes.every(r => inside(r, a))) throw Error("The configured gap does not fit this work area.");
    return boxes;
}
function normalize(r, a, tolerance = 0) {
    if (!inside(r, a, tolerance)) throw Error("Move each selected frame fully inside its output work area first.");
    const edges = [(r.x-a.x)/a.width, (r.y-a.y)/a.height, (r.x+r.width-a.x)/a.width, (r.y+r.height-a.y)/a.height];
    return edges.map(v => Math.max(0, Math.min(v, 1)));
}
function project(edges, a) {
    const [l,t,r,b] = edges.map((v,i) => {
        const extent = i % 2 ? a.height : a.width;
        return v === 1 ? extent : Math.min(extent, Math.round(v * extent));
    });
    return rect(a.x+l, a.y+t, r-l, b-t);
}
