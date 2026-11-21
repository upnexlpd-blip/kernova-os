// Run with node tests/window_tools.js. No display or third-party dependencies.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const test = require("node:test");
const source = file => fs.readFileSync("apps/window-tools/"+file+".js","utf8");
const layout = vm.runInNewContext(source("layout")+";({rect, preset, inside, normalize, project})");
const bounds = {x:-1280,y:27,width:1279.5,height:760.5};

test("Logical work areas, negative origin, fractional edges, panel, odd gaps and exact arity", () => {
    for (const [name,n] of [["Side",2],["Coding",3]]) {
        const boxes = layout.preset(name,n,bounds,9);
        assert.equal(boxes.length,n);
        assert.equal(boxes[0].x,-1280);
        assert.equal(boxes[0].y,27);
        assert.equal(boxes[1].x-boxes[0].x-boxes[0].width,9);
        assert.equal(boxes[1].x+boxes[1].width,bounds.x+bounds.width);
        assert.ok(boxes.every(b => layout.inside(b,bounds)));
        assert.throws(() => layout.preset(name,n-1,bounds,8));
    }
    assert.throws(() => layout.preset("Side",2,{x:8,y:3,width:6,height:10},8));
    const box = {x:-1240,y:47,width:280,height:210};
    const edges = layout.normalize(box,bounds);
    const projected = layout.project(edges,{x:100,y:-500,width:2559,height:1521});
    assert.deepEqual({...projected},{x:180,y:-460,width:560,height:420});
});

class Signal {
    constructor() { this.handlers = new Set(); }
    connect(fn) { this.handlers.add(fn); }
    disconnect(fn) { this.handlers.delete(fn); }
    fire(...args) { for (const fn of [...this.handlers]) fn(...args); }
}
function fixture() {
    const timers=[];
    class Timer {
        constructor() { this.timeout=new Signal(); timers.push(this); }
        start() { this.running=true; }
        stop() { this.running=false; }
    }
    const output={name:"A"}, desktop={id:1};
    const ws={screens:[output],currentDesktop:desktop,currentActivity:"a",clientArea:() => bounds};
    for (const kind of ["screensChanged","currentDesktopChanged","currentActivityChanged","windowRemoved"]) ws[kind]=new Signal();
    const shortcuts={}, messages=[], flags={};
    let menu;
    const ctx=vm.createContext({QTimer:Timer,KWin:{MaximizeArea:1},workspace:ws,
        readConfig:(key,defaultValue)=>defaultValue,
        registerUserActionsMenu:fn=>{menu=fn;},
        registerShortcut:(key,title,shortcut,fn)=>{assert.equal(shortcut,""); shortcuts[key]=fn;},
        callDBus:(dest,path,iface,method,...args)=>{
            if (method==="isScriptLoaded") args[1](!!flags[args[0]]);
            else if (method==="ListActivatableNames") args[0](["org.kernova.WindowTemplates"]);
            else if (method==="GetActive") args[0](false);
            else if (method==="showText") messages.push(args[1]);
        }});
    vm.runInContext(["layout","kwin","operations"].map(source).join("\n"),ctx);
    function window(offset) {
        const w={normalWindow:true,managed:true,desktops:[desktop],activities:[],resizeable:true,moveable:true,
            maximizeMode:0,moveableAcrossScreens:true,output,minSize:{width:1,height:1},maxSize:{width:9999,height:9999},
            caption:"same app",resourceClass:"qa"};
        for (const name of ["interactiveMoveResizeStarted","maximizedChanged","tileChanged","desktopsChanged",
            "activitiesChanged","fullScreenChanged","minimizedChanged","shadeChanged","frameGeometryChanged"]) w[name]=new Signal();
        let frame={x:-1250+offset,y:50+offset,width:300,height:220};
        Object.defineProperty(w,"frameGeometry",{get:()=>frame,set:r=>{
            if (!w.refuse) { frame={...r}; w.frameGeometryChanged.fire(); }
        }});
        Object.defineProperty(w,"clientGeometry",{get:()=>frame});
        return w;
    }
    function act(id,w) { ws.activeWindow=w; shortcuts["org.kernova.windowtools."+id](); }
    function settle() { for (let i=0;i<40;i++) for (const t of timers) if (t.running) t.timeout.fire(); }
    return {ws,act,window,settle,messages,flags,output,ctx,menu};
}
test("Preflight preserves prior undo, interaction invalidates ownership even after moving back",()=>{
    const f=fixture(), a=f.window(0), b=f.window(20);
    const origA=a.frameGeometry,origB=b.frameGeometry;
    f.act("Add",b); f.act("Add",a); f.act("Add",b); f.act("Side"); f.settle();
    assert.equal(b.frameGeometry.x,bounds.x);
    assert.ok(a.frameGeometry.x>b.frameGeometry.x);
    f.act("Coding"); assert.match(f.messages.at(-1),/exactly 3/);
    const placed=a.frameGeometry;
    a.frameGeometry=origA; a.frameGeometry=placed;
    f.act("Undo"); f.settle();
    assert.deepEqual(b.frameGeometry,origB);
    assert.deepEqual(a.frameGeometry,placed);
    assert.match(f.messages.at(-1),/1 of 2/);
});
test("Refusal triggers bounded verified rollback; changed topology expires undo",()=>{
    const f=fixture(), a=f.window(0), b=f.window(20);
    const orig=a.frameGeometry;
    f.act("Add",a); f.act("Add",b); b.refuse=true;
    f.act("Side"); f.settle(); assert.deepEqual(a.frameGeometry,orig);
    assert.match(f.messages.at(-1),/Rollback restored 1 of 2/);
    b.refuse=false; f.act("Side"); f.settle();
    const placed=a.frameGeometry;
    f.ws.screens=[]; f.ws.screensChanged.fire(); f.ws.screens=[f.output];
    f.act("Undo"); f.settle(); assert.deepEqual(a.frameGeometry,placed);
    assert.match(f.messages.at(-1),/0 of 2/);
});
test("Ineligible windows, fixed minimum, conflicts, closed slot and ambiguous connector",()=>{
    const f=fixture(),a=f.window(0),b=f.window(20);
    f.flags.polonium=true; f.act("Add",a); assert.match(f.messages.at(-1),/polonium/);
    f.flags.polonium=false;
    for (const [key,value] of [["maximizeMode",3],["tile",{}],["transient",true],["fullScreen",true],["resizeable",false]]) {
        const old=a[key]; a[key]=value; f.act("Add",a); assert.doesNotMatch(f.messages.at(-1),/Added/); a[key]=old;
    }
    f.act("Add",a); f.act("Add",b);
    const orig=a.frameGeometry;
    b.minSize.width=800; f.act("Side"); f.settle(); assert.deepEqual(a.frameGeometry,orig);
    assert.match(f.messages.at(-1),/size limits/);
    f.ws.windowRemoved.fire(b); f.act("Side"); assert.match(f.messages.at(-1),/exactly 2/);
    f.ws.screens.push({name:"A"});
    assert.throws(()=>vm.runInContext('uniqueOutput("A")',f.ctx),/Reconnect/);
    assert.throws(()=>vm.runInContext('uniqueOutput("missing")',f.ctx),/Reconnect/);
});
test("Closing or interacting during an asynchronous request never moves the surviving user's frame back",()=>{
    const f=fixture(),a=f.window(0),b=f.window(20);
    f.act("Add",a); f.act("Add",b); f.act("Side");
    a.interactiveMoveResizeStarted.fire();
    const manual={x:-1050,y:80,width:300,height:220};
    a.frameGeometry=manual;
    f.ws.windowRemoved.fire(b);
    f.settle();
    assert.deepEqual(a.frameGeometry,manual);
    assert.match(f.messages.at(-1),/0 of 2/);
});
