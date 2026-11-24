"""Select, download and remove models from the local Ollama store."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QListWidget, QListWidgetItem, QProgressBar,
    QPushButton, QVBoxLayout,
)

from runtime import load_catalog
from widgets import Work, confirm, error_text, label


class ModelLibrary(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.t = parent.t
        self.client = parent.client
        self.names = set(parent.names)
        self.entries = {}
        self.job = None
        self.operation = ""
        self.retry_tag = None
        self.setWindowTitle(self.t("library"))
        self.resize(620, 425)
        layout = QVBoxLayout(self)
        self.listing = QListWidget()
        self.listing.setAccessibleName(self.t("library"))
        layout.addWidget(self.listing, 1)
        self.details = label()
        layout.addWidget(self.details)
        self.progress = QProgressBar()
        self.progress.hide()
        layout.addWidget(self.progress)
        self.status = label(self.t("loading"))
        layout.addWidget(self.status)
        row = QHBoxLayout()
        self.install = QPushButton(self.t("download"))
        self.remove = QPushButton(self.t("remove_model"))
        self.stop = QPushButton(self.t("stop"))
        self.close_button = QPushButton(self.t("close"))
        for button in (self.install, self.remove, self.stop, self.close_button):
            row.addWidget(button)
        layout.addLayout(row)
        self.listing.currentRowChanged.connect(self.select)
        self.install.clicked.connect(self.download)
        self.remove.clicked.connect(self.delete)
        self.close_button.clicked.connect(self.reject)
        self.stop.clicked.connect(self.cancel)
        self.run("catalog", lambda token, update: load_catalog())

    def tag(self):
        item = self.listing.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def populate(self, selected=None):
        self.listing.clear()
        tags = [*self.entries, *sorted(self.names.difference(self.entries))]
        for tag in tags:
            state = self.t("installed" if tag in self.names else "available")
            item = QListWidgetItem(f"{tag}    ·    {state}")
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.listing.addItem(item)
        if tags:
            self.listing.setCurrentRow(tags.index(selected) if selected in tags else 0)

    def select(self):
        tag = self.tag()
        entry = self.entries.get(tag)
        if entry:
            self.details.setText(self.t("model_detail", purpose=entry["purpose"][self.t.language],
                                        size=f'{entry["size"] / 1e9:.2f}',
                                        license=entry["license"], url=entry["url"]))
        elif tag:
            self.details.setText(self.t("external_model"))
        else:
            self.details.clear()
        idle = self.job is None
        self.install.setText(self.t("retry" if tag and tag == self.retry_tag else "download"))
        self.install.setEnabled(idle and bool(entry) and tag not in self.names)
        self.remove.setEnabled(idle and tag in self.names)
        self.listing.setEnabled(idle)
        self.stop.setEnabled(self.operation == "download" and not idle)

    def run(self, operation, function):
        self.operation = operation
        self.job = Work(function, self)
        self.job.update.connect(self.on_progress)
        self.job.finished.connect(self.on_done)
        self.select()
        self.job.start()

    def download(self):
        entry = self.entries[self.tag()]
        self.retry_tag = entry["tag"]
        self.status.setText(self.t("downloading"))
        self.progress.setRange(0, 0)
        self.progress.show()
        self.run("download", lambda token, update: self.client.install(
            entry, token, lambda status, done, total: update((status, done, total))))

    def on_progress(self, progress):
        status, done, total = progress
        if status.startswith("verifying"):
            stage = self.t("verifying")
        elif status.startswith(("Importing", "parsing", "creating", "writing", "using existing")):
            stage = self.t("importing")
        else:
            stage = self.t("downloading")
        if total > 0:
            self.progress.setRange(0, 100)
            self.progress.setValue(min(100, int(done * 100 / total)))
            self.status.setText(f"{stage}   {done / 1e6:.0f} / {total / 1e6:.0f} MB")
        else:
            self.progress.setRange(0, 0)
            self.status.setText(stage)

    def cancel(self):
        if self.job and self.operation == "download":
            self.job.token.cancel()
            self.stop.setEnabled(False)
            self.status.setText(self.t("stopping"))

    def delete(self):
        tag = self.tag()
        if confirm(self, self.t("remove_model"), self.t("confirm_model", tag=tag)):
            self.run("delete", lambda token, update: self.client.delete(tag))

    def on_done(self, result, error):
        self.job.deleteLater()
        self.job = None
        self.progress.hide()
        tag = self.tag()
        if error:
            self.status.setText(error_text(self.t, error))
        elif self.operation == "catalog":
            entries, warning = result
            self.entries = {entry["tag"]: entry for entry in entries}
            self.status.setText(self.t("fallback", detail=warning) if warning else "")
        elif self.operation == "download":
            self.names.add(tag)
            self.retry_tag = None
            self.status.setText(self.t("downloaded", tag=tag))
        else:
            self.names.discard(tag)
            self.status.clear()
        self.populate(tag)
        self.select()

    def reject(self):
        if self.job:
            self.cancel()
            return
        super().reject()

    def closeEvent(self, event):
        if self.job:
            self.cancel()
            event.ignore()
        else:
            super().closeEvent(event)
