#!/usr/bin/python3
"""KERNOVA desktop controls for workload profiles and system updates."""
from collections import deque
import gzip
from pathlib import Path
import shlex
import subprocess
import sys
import zlib

from PySide6.QtCore import QObject, QProcess, QSettings, QThreadPool, Signal, Slot
from PySide6.QtWidgets import (QApplication, QComboBox, QLabel, QLineEdit, QMainWindow,
                               QPlainTextEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget)
from profiles import PROFILES, power_modes


def recent_history(directory, limit=12):
    dated = []
    for path in directory.glob("history.log*"):
        try:
            dated.append((path.stat().st_mtime, path))
        except OSError:
            continue  # The log may have rotated after glob().
    records = []
    for _, path in sorted(dated, reverse=True):
        recent = deque(maxlen=limit - len(records))
        lines = []
        try:
            with (gzip.open if path.suffix == ".gz" else open)(path, "rt", errors="replace") as log:
                for line in log:
                    if line.strip():
                        lines.append(line)
                    elif lines:
                        recent.append("".join(lines).strip())
                        lines.clear()
                if lines:
                    recent.append("".join(lines).strip())
        except (OSError, EOFError, zlib.error):
            continue
        records.extend(reversed(recent))
        if len(records) == limit:
            break
    return "\n\n".join(records) or "No APT history available."


class SystemQueries(QObject):
    profiles = Signal(object)
    updates = Signal(str, str)

    def read_profiles(self):
        self.profiles.emit(power_modes())

    def read_updates(self):
        version = "Package information unavailable."
        try:
            info = subprocess.run(["apt-cache", "policy", "kernova-desktop"], capture_output=True,
                                  text=True, errors="replace", timeout=10, check=True)
            version = "\n".join(info.stdout.splitlines()[1:3]).strip() or version
        except (OSError, subprocess.SubprocessError):
            pass
        if Path("/run/reboot-required").exists():
            version += "\nRestart required to finish installing updates."
        self.updates.emit(version, recent_history(Path("/var/log/apt")))


class Center(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KERNOVA Performance Center")
        self.resize(570, 410)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.tabs.addTab(panel, "Smart Performance")
        self.mode = QComboBox()
        for key, profile in PROFILES.items():
            self.mode.addItem(profile.label, key)
        self.settings = QSettings("KERNOVA", "SmartPerformance")
        self.mode.setCurrentIndex(max(0, self.mode.findData(self.settings.value("profile", "gaming"))))
        self.detail = QLabel()
        self.detail.setWordWrap(True)
        self.hardware = set()
        self.queries = SystemQueries()
        self.queries.profiles.connect(self.show_profiles)
        self.queries.updates.connect(self.show_updates)
        self.mode.currentIndexChanged.connect(self.describe)
        self.command = QLineEdit()
        self.command.setPlaceholderText("Program and arguments, e.g. kate --new")
        launch = QPushButton("Launch with profile")
        launch.clicked.connect(self.launch)
        self.command.returnPressed.connect(self.launch)
        self.feedback = QLabel()
        self.feedback.setWordWrap(True)
        for widget in (self.mode, self.detail, self.command, launch, self.feedback):
            layout.addWidget(widget)
        layout.addStretch()
        self.describe()
        self.jobs = set()

        updates = QWidget()
        box = QVBoxLayout(updates)
        self.tabs.addTab(updates, "System updates")
        self.versions = QLabel()
        self.history = QPlainTextEdit()
        self.history.setReadOnly(True)
        self.history.setAccessibleName("APT update history")
        self.refresh = QPushButton("Refresh package information")
        self.refresh.clicked.connect(self.read_updates)
        discover = QPushButton("Check and install updates in Discover")
        discover.clicked.connect(lambda: QProcess.startDetached("plasma-discover", ["--mode", "Update"]))
        for widget in (self.versions, self.refresh, discover, QLabel("APT transaction history"), self.history):
            box.addWidget(widget)
        self.tabs.currentChanged.connect(lambda i: self.read_updates() if i == 1 else None)
        QThreadPool.globalInstance().start(self.queries.read_profiles)

    @Slot(object)
    def show_profiles(self, modes):
        self.hardware = modes
        self.describe()

    def describe(self):
        key = self.mode.currentData()
        p = PROFILES[key]
        hardware = (f"Requests the {p.power} power profile while this program runs."
                    if p.power and p.power in self.hardware else "Uses process scheduling on this device.")
        self.detail.setText(f"{p.description} {hardware} Close the launched program to end the profile.")
        self.settings.setValue("profile", key)

    def launch(self):
        try:
            argv = shlex.split(self.command.text())
        except ValueError as exc:
            self.feedback.setText(str(exc))
            return
        if not argv:
            self.feedback.setText("Enter the program you want to run.")
            return
        # Track running programs so closing the controls preserves the workload.
        job = QProcess(self)
        self.jobs.add(job)
        job.setProgram("/usr/bin/kernova-performance-run")
        job.setArguments([self.mode.currentData(), "--", *argv])
        job.setStandardOutputFile(QProcess.nullDevice())
        # Keep the parent alive while a workload runs, even when its window closes.
        def cleanup():
            self.jobs.discard(job)
            job.deleteLater()
            if not self.jobs and not self.isVisible():
                QApplication.quit()

        def finished(code, status):
            self.feedback.setText("Program finished." if code == 0 else f"Program exited with status {code}.")
            cleanup()

        def failed(error):
            if error == QProcess.ProcessError.FailedToStart:
                self.feedback.setText(job.errorString())
                cleanup()

        message = "Started " + argv[0] + " with " + self.mode.currentText() + "."
        job.started.connect(lambda: self.feedback.setText(message))
        job.finished.connect(finished)
        job.errorOccurred.connect(failed)
        job.setStandardErrorFile(QProcess.nullDevice())
        job.start()

    def closeEvent(self, event):
        if self.jobs:
            self.hide()
            event.ignore()
        else:
            super().closeEvent(event)

    def read_updates(self):
        if self.refresh.isEnabled():
            self.refresh.setEnabled(False)
            self.versions.setText("Reading package information…")
            QThreadPool.globalInstance().start(self.queries.read_updates)

    @Slot(str, str)
    def show_updates(self, version, history):
        self.versions.setText(version)
        self.history.setPlainText(history)
        self.refresh.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    center = Center()
    if "--updates" in sys.argv:
        center.tabs.setCurrentIndex(1)
    center.show()
    sys.exit(app.exec())
