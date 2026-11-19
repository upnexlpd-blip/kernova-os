const weather = "org.kernova.weather";
if (knownWidgetTypes.includes(weather)) {
    for (const panel of panels()) {
        if (panel.location !== "bottom" || panel.widgets(weather).length) {
            continue;
        }
        const clock = panel.widgets("org.kde.plasma.digitalclock")[0];
        if (clock) {
            const index = clock.index;
            const applet = panel.addWidget(weather);
            if (applet && index >= 0) {
                applet.index = index;
            }
        }
    }
}
