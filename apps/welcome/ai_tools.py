"""Installation entry points for cloud development tools and local AI models."""

import os
from pathlib import Path
import shutil
import sys

from PySide6.QtCore import QLocale, QProcess, QProcessEnvironment, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import QApplication, QFrame, QGridLayout, QLabel, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget

from main import ICON_FILE, ICON_NAME, heading, label
from system_info import language_for


CODEX_GUIDE = "https://learn.chatgpt.com/docs/codex/cli"
CLAUDE_GUIDE = "https://code.claude.com/docs/en/setup"
CURSOR_DOWNLOAD = "https://cursor.com/download"
ALPACA_FLATHUB = "https://flathub.org/apps/com.jeffser.Alpaca"
CODEX_INSTALLER = ("https://chatgpt.com/codex/install.sh", "/bin/sh")
CLAUDE_INSTALLER = ("https://claude.ai/install.sh", "/bin/bash", "stable")
INSTALL = """set -eu
if [ "$(id -u)" -eq 0 ]; then
    printf '%s\\n' "$1" >&2
    exit 1
fi
shift
url=$1
interpreter=$2
shift 2
installer=$(mktemp)
trap 'rm -f -- "$installer"' 0
trap 'exit 130' INT
trap 'exit 143' TERM
/usr/bin/curl -q --fail --show-error --silent --location --proto '=https' --proto-redir '=https' \\
    --connect-timeout 15 --max-time 90 --output "$installer" "$url"
"$interpreter" "$installer" "$@"
"""

STRINGS = {
    "title": ("AI Tools", "Алатки за ВИ"),
    "intro": (
        "Downloads require internet access. Sign in to Codex, Claude Code or Cursor in the tool after installation.",
        "За преземање е потребен интернет. По инсталацијата, најавете се во Codex, Claude Code или Cursor преку самата алатка.",
    ),
    "codex": (
        "Install the OpenAI command-line tool for your account. Run ~/.local/bin/codex to start it.",
        "Инсталирајте ја командната алатка на OpenAI за вашата сметка. Стартувајте ја со ~/.local/bin/codex.",
    ),
    "claude": (
        "Install the Anthropic command-line tool for your account. Run ~/.local/bin/claude to start it.",
        "Инсталирајте ја командната алатка на Anthropic за вашата сметка. Стартувајте ја со ~/.local/bin/claude.",
    ),
    "cursor": (
        "Choose Linux .deb (x64). Open the downloaded package with Discover or install it with APT as an administrator.",
        "Изберете Linux .deb (x64). Отворете го пакетот во Discover или инсталирајте го преку APT како администратор.",
    ),
    "alpaca": (
        "Install Alpaca and download a model inside the app. Downloaded local models can run offline.",
        "Инсталирајте ја Alpaca и преземете модел во апликацијата. Преземените локални модели работат без интернет.",
    ),
    "install": ("Install", "Инсталирај"),
    "launch": ("Open in Konsole", "Отвори во Konsole"),
    "installing": ("Installing {name}…", "Се инсталира {name}…"),
    "installed": ("{name} is ready. Choose Open in Konsole to start it.", "{name} е подготвен. Изберете Отвори во Konsole."),
    "failed": ("Could not install {name}. Check the output below and try again.", "Инсталацијата на {name} не успеа. Проверете го извештајот и обидете се повторно."),
    "busy": ("Keep AI Tools open until the installation finishes.", "Оставете го овој прозорец отворен додека заврши инсталацијата."),
    "download": ("Open download page", "Отвори ја страницата за преземање"),
    "discover": ("Open in Discover", "Отвори во Discover"),
    "live": (
        "In a Live session, installations and model downloads are temporary and are lost when you restart.",
        "Во Live сесија, инсталациите и преземените модели се привремени и се бришат при рестартирање.",
    ),
    "root": (
        "Open KERNOVA AI Tools from your own desktop account to install this tool.",
        "Отворете ги алатките за ВИ од вашата корисничка сметка за да ја инсталирате оваа алатка.",
    ),
    "terminal_failed": (
        "Konsole could not start. Opening the official installation guide.",
        "Konsole не се стартува. Се отвора официјалното упатство за инсталација.",
    ),
    "discover_failed": (
        "Discover could not start. Opening Alpaca on Flathub.",
        "Discover не се стартува. Се отвора страницата на Alpaca на Flathub.",
    ),
    "browser_failed": (
        "The browser could not open this address. {url}",
        "Прелистувачот не ја отвори оваа адреса. {url}",
    ),
}


class AIToolsWindow(QScrollArea):
    def __init__(self, locale_name: str):
        super().__init__()
        self.language_index = int(language_for(locale_name) == "mk")
        self.setWindowTitle(self.text("title"))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidgetResizable(True)
        self.resize(760, 530)
        self.buttons = {}
        self.active_tool = None
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.install_finished)
        self.process.errorOccurred.connect(self.install_error)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(heading(self.text("title"), 1.55))
        layout.addWidget(label(self.text("intro")))

        rows = QGridLayout()
        rows.setColumnStretch(1, 1)
        rows.setHorizontalSpacing(18)
        rows.setVerticalSpacing(12)
        tools = (
            ("Codex CLI", "codex", "install", lambda: self.install("codex", CODEX_INSTALLER, CODEX_GUIDE)),
            ("Claude Code", "claude", "install", lambda: self.install("claude", CLAUDE_INSTALLER, CLAUDE_GUIDE)),
            ("Cursor", "cursor", "download", lambda: self.open_page(CURSOR_DOWNLOAD)),
            ("Alpaca", "alpaca", "discover", self.open_alpaca),
        )
        for row, (name, description, action, launch) in enumerate(tools):
            tool = QVBoxLayout()
            tool.setSpacing(3)
            tool.addWidget(heading(name, 1.10))
            tool.addWidget(label(self.text(description)))
            icon = QLabel()
            icon.setPixmap(QIcon(str(Path(__file__).with_name("icons") / f"{description}.svg")).pixmap(40, 40))
            rows.addWidget(icon, row, 0, Qt.AlignmentFlag.AlignVCenter)
            rows.addLayout(tool, row, 1)
            button = QPushButton(self.text(action))
            button.setAccessibleName(f"{name} · {self.text(action)}")
            button.clicked.connect(launch)
            if action == "install":
                self.buttons[description] = (name, button)
                self.refresh_button(description)
            rows.addWidget(button, row, 2, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(rows)

        layout.addWidget(label(self.text("live")))
        self.status = label("")
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status.hide()
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(250)
        self.output.setFixedHeight(105)
        self.output.hide()
        layout.addWidget(self.output)
        layout.addStretch()
        self.setWidget(panel)

    def text(self, key: str, **values: str) -> str:
        return STRINGS[key][self.language_index].format(**values)

    def show_status(self, key: str, **values: str):
        self.status.setText(self.text(key, **values))
        self.status.show()

    def open_page(self, url: str):
        if not QDesktopServices.openUrl(QUrl(url)):
            self.show_status("browser_failed", url=url)

    @staticmethod
    def executable(tool):
        local = Path.home() / ".local" / "bin" / tool
        if local.is_file() and os.access(local, os.X_OK):
            return str(local)
        return shutil.which(tool)

    def refresh_button(self, tool):
        name, button = self.buttons[tool]
        caption = self.text("launch" if self.executable(tool) else "install")
        button.setText(caption)
        button.setAccessibleName(f"{name} · {caption}")

    def install(self, tool: str, installer: tuple[str, ...], guide: str):
        executable = self.executable(tool)
        if executable:
            started, _ = QProcess.startDetached("/usr/bin/konsole", ["--separate", "-e", executable])
            if not started:
                self.show_status("terminal_failed")
                self.open_page(guide)
            return
        if self.active_tool:
            return
        self.active_tool = tool
        for _, button in self.buttons.values():
            button.setEnabled(False)
        self.show_status("installing", name=self.buttons[tool][0])
        self.output.clear()
        self.output.show()
        self.progress.show()
        self.ensureWidgetVisible(self.output)
        env = QProcessEnvironment.systemEnvironment()
        if tool == "codex":
            env.insert("CODEX_NON_INTERACTIVE", "1")
        self.process.setProcessEnvironment(env)
        self.process.start("/bin/sh", ["-c", INSTALL, "kernova-ai-tools", self.text("root"), *installer])
        self.process.closeWriteChannel()

    def read_output(self):
        data = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            self.output.insertPlainText(data.replace("\r", "\n"))
            self.output.ensureCursorVisible()

    def install_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.output.appendPlainText(self.process.errorString())
            self.install_finished(1, QProcess.ExitStatus.CrashExit)

    def install_finished(self, code, status):
        tool = self.active_tool
        if not tool:
            return
        self.read_output()
        self.active_tool = None
        success = code == 0 and status == QProcess.ExitStatus.NormalExit and self.executable(tool)
        self.show_status("installed" if success else "failed", name=self.buttons[tool][0])
        self.progress.hide()
        for key, (_, button) in self.buttons.items():
            self.refresh_button(key)
            button.setEnabled(True)
        self.ensureWidgetVisible(self.status)

    def closeEvent(self, event):
        if self.active_tool:
            self.show_status("busy")
            self.ensureWidgetVisible(self.status)
            event.ignore()
            return
        super().closeEvent(event)

    def open_alpaca(self):
        started, _ = QProcess.startDetached("/usr/bin/kernova-get-apps", ["alpaca"])
        if not started:
            self.show_status("discover_failed")
            self.open_page(ALPACA_FLATHUB)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("kernova-ai-tools")
    app.setDesktopFileName("kernova-ai-tools")
    app.setWindowIcon(QIcon.fromTheme(ICON_NAME, QIcon(str(ICON_FILE))))
    window = AIToolsWindow(QLocale.system().name())
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
