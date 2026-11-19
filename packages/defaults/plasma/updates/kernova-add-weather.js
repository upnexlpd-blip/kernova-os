const weather = "org.kernova.weather";
if (knownWidgetTypes.includes(weather)) {
    for (const panel of panels()) {
        if (panel.location !== "bottom" || panel.widgets(weather).length) {
            continue;
        }
        const clock = panel.widgets("org.kde.plasma.digitalclock")[0];
        if (!clock) {
            continue;
        }
        // Plasma 6.3 uses this order to construct the panel at startup.
        panel.currentConfigGroup = ["General"];
        const savedOrder = String(panel.readConfig("AppletOrder", ""));
        const order = savedOrder ? savedOrder.split(";") : panel.widgetIds.map(String);
        const position = order.indexOf(String(clock.id));
        const applet = panel.addWidget(weather);
        if (applet && position >= 0) {
            order.splice(position, 0, String(applet.id));
            panel.writeConfig("AppletOrder", order.join(";"));
        }
    }
}
