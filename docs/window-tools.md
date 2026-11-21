# KERNOVA Window Tools for KWin

Window Tools 0.1.23 targets the KERNOVA Debian 13 Plasma Wayland session, KWin and Plasma 6.3.6, and Qt 6.8.2. Native Wayland and Xwayland clients share the compositor's logical coordinate system.

## Installation and activation

On an installed KERNOVA desktop with the stable update source, open **Discover → Updates → Refresh → Update All**. Upgrading `kernova-desktop` to `0.1.23+stable1` installs the matching Window Tools package in the same transaction. The script starts disabled on first installation and retains existing users' preferences.

Open **System Settings → Window Management → KWin Scripts**, check **KERNOVA Window Tools**, then **Apply**. The settings button beside the script selects the gap (default 8 logical pixels) and one of eight numbered template slots. After saving the dialog, use **Extensions → KERNOVA Window Tools → Reload saved settings** in a window's title-bar menu. The on-screen message confirms the effective gap and slot. System Settings → Keyboard → Shortcuts → KWin lists actions under **KERNOVA Window Tools**. All bindings start unassigned. If the script was already running during an upgrade, uncheck it and click **Apply**, then check it and click **Apply** to load the new code immediately. This starts a fresh selection and undo history.

## Arrange open windows

Open a window's title-bar menu (Alt+F3). Under **Extensions → KERNOVA Window Tools**, add that window. Repeat in the order you want. **Show selection order**, **Remove window from selection** and **Clear selection** manage the list. Shortcuts operate on the active window. Adding a window twice retains its first slot. Closing it removes its slot.

- **Side by Side** needs two windows. First goes left, second right.
- **Coding layout** needs three. First takes the left 60% of the space after the gap. Second goes upper right, third lower right.
- Both use the usable work area of the first selected window's output. KWin supplies the logical coordinates and the panel reservations. Windows keep their desktops and activities.
- Select ordinary, movable and resizable windows on the current desktop and activity. Return maximized, tiled, shaded, minimized or fullscreen windows to floating first. Place starting frames inside the work area. Fixed-size and transient windows are unsupported. An application or window rule can still decline a request. Window Tools checks the resulting frames for about 1.5 seconds and reports incomplete placement.

## Templates and Undo

Choose a template slot in KWin Scripts settings. **Save selection to template** replaces that slot, retaining the window order and normalized frame edges per output. **Apply template** uses the current selection in order. **List saved templates** shows occupied slots and **Delete template** clears the chosen slot. Use a new slot to keep an older arrangement. One to eight windows can be saved. Resize and resolution changes are handled by scaling the edges to each output's current usable area. Reconnect the original connector or save a new arrangement if an output name is missing or ambiguous.

An on-demand user session D-Bus service stores each numbered slot in `$XDG_DATA_HOME/kernova/window-tools/` (default `~/.local/share/kernova/window-tools/`). It exits after 30 idle seconds. Templates contain connector names and frame edges. A selection, captions and undo records live only in the compositor session.

**Undo last layout** restores positions and frame sizes for the last changed layout. Closing a window, interacting with its frame, changing its desktop/activity, or changing its work area can invalidate its entry. When a window or rule refuses a placement, the extension attempts rollback only for frames it still owns and reports the count. A rejected preflight preserves a preceding undo. Starting another geometry operation replaces it.

To stop Window Tools, clear its checkbox in KWin Scripts and click **Apply**. This keeps the desktop metapackage, templates and shortcut settings installed. Removing the required Window Tools package would also remove the KERNOVA desktop metapackage.

Known automatic tilers (Krohnkite, Bismuth, Polonium, Karousel, kwin-tiling) block actions while loaded. Choose which to enable in KWin Scripts. Other third-party scripts and custom rules may also control geometry.

## Validation

On an isolated installed KERNOVA VM, two native Wayland windows from one application and an Xwayland window exercised both presets, selection order, template save and reload, full undo and preservation of manual changes. Closing a selected window and selecting a fixed-size, maximized or tiled window were also tested. A client that withheld its Wayland configure acknowledgement caused the other window to roll back. A late client acknowledgement can still arrive after a reported timeout.

A second run used two virtual displays at 100% and 125%. Cross-output preset placement and undo, template reapplication after a resolution change, and declining a missing connector passed. KWin normalized the leftmost virtual output's origin to zero. At 125% scale, a requested height of 294 logical pixels produced a 295.2-pixel frame. Verification allows two logical pixels at fractional scales and one at integral scales. Preset targets use the work area supplied by KWin. Unit tests cover negative origins, unavailable and ambiguous outputs, incompatible constraints, topology loss, malformed data and interrupted writes. Physical mixed-DPI monitors, connector hot-unplug and a standalone X11 session have no graphical validation in this release.

Run `node tests/window_tools.js` and `python3 -m unittest discover -s tests -p test_window_templates.py` from the checkout. For the graphical test, install the candidate in a disposable unlocked Plasma Wayland account and run `python3 tests/window-tools-live/session.py` inside that session. Use a fresh test account with default script settings. The test changes the KWin Scripts preference, uses template slots 1 and 5, and opens its own example windows.

KDE references: [KWin scripting](https://develop.kde.org/docs/plasma/kwin/), [scripting API](https://develop.kde.org/docs/plasma/kwin/api/), [KWin 6.3.6 source](https://invent.kde.org/plasma/kwin/-/tree/v6.3.6).
