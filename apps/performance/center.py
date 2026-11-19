#!/usr/bin/python3
"""KERNOVA desktop controls for workload profiles and system updates."""
import gzip
from pathlib import Path
import shlex
import subprocess
import sys

from PySide6.QtCore import QProcess, QSettings
from PySide6.QtWidgets import (QApplication, QComboBox, QLabel, QLineEdit, QMainWindow,
                               QPlainTextEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget)
from profiles import PROFILES, power_modes


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
        self.hardware = power_modes()
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
        refresh = QPushButton("Refresh package information")
        refresh.clicked.connect(self.read_updates)
        discover = QPushButton("Check and install updates in Discover")
        discover.clicked.connect(lambda: QProcess.startDetached("plasma-discover", ["--mode", "Update"]))
        for widget in (self.versions, refresh, discover, QLabel("APT transaction history"), self.history):
            box.addWidget(widget)
        self.tabs.currentChanged.connect(lambda i: self.read_updates() if i == 1 else None)

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
        def finished(code, status):
            self.feedback.setText("Program finished." if code == 0 else f"Program exited with status {code}.")
            self.jobs.discard(job)
            job.deleteLater()
            if not self.jobs and not self.isVisible():
                QApplication.quit()
        job.finished.connect(finished)
        job.setStandardErrorFile(QProcess.nullDevice())
        job.start()
        if not job.waitForStarted(1000):
            self.jobs.discard(job)
            self.feedback.setText(job.errorString())
            job.deleteLater()
            return
        self.feedback.setText("Started " + argv[0] + " with " + self.mode.currentText() + ".")

    def closeEvent(self, event):
        if self.jobs:
            self.hide()
            event.ignore()
        else:
            super().closeEvent(event)

    def read_updates(self):
        info = subprocess.run(["apt-cache", "policy", "kernova-desktop"], capture_output=True, text=True)
        self.versions.setText("\n".join(info.stdout.splitlines()[1:3]).strip() or "Package information unavailable.")
        if Path("/run/reboot-required").exists():
            self.versions.setText(self.versions.text() + "\nRestart required to finish installing updates.")
        records = []
        for path in sorted(Path("/var/log/apt").glob("history.log*"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                with (gzip.open if path.suffix == ".gz" else open)(path, "rt", errors="replace") as log:
                    records.extend(reversed(log.read().strip().split("\n\n")))
            except OSError:
                continue
            if len(records) >= 12:
                break
        self.history.setPlainText("\n\n".join(records[:12]).strip() or "No APT history available.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    center = Center()
    if "--updates" in sys.argv:
        center.tabs.setCurrentIndex(1)
    center.show()
    sys.exit(app.exec())
