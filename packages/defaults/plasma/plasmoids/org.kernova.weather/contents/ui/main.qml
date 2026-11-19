import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.plasma5support as Plasma5Support

PlasmoidItem {
    id: root

    property string temperature: ""
    property string city: ""
    readonly property string readCommand: "/usr/bin/kernova-weather-panel"
    readonly property string openCommand: "/usr/bin/kernova-weather-panel --open"

    preferredRepresentation: compactRepresentation
    toolTipMainText: city || i18n("Weather")
    toolTipSubText: temperature ? i18n("Open forecast for %1", city) : i18n("Open Weather to view a forecast")

    compactRepresentation: PlasmaComponents.ToolButton {
        text: root.temperature
        icon.name: root.temperature ? "" : "weather-clear-symbolic"
        Accessible.name: root.city ? i18n("Weather in %1: %2", root.city, root.temperature) : i18n("Open Weather")
        Layout.minimumWidth: implicitWidth
        onClicked: commands.connectSource(root.openCommand)
    }

    Plasma5Support.DataSource {
        id: commands
        engine: "executable"
        onNewData: (source, data) => {
            disconnectSource(source)
            if (source !== root.readCommand) {
                return
            }
            const result = data["exit code"] === 0 ? JSON.parse(data.stdout || "{}") : {}
            root.temperature = result.temperature || ""
            root.city = result.city || ""
        }
    }

    Timer {
        interval: 300000
        repeat: true
        running: true
        triggeredOnStart: true
        onTriggered: commands.connectSource(root.readCommand)
    }
}
