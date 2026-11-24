"""Select, search, download and remove free local models from the Ollama store."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QProgressBar,
    QPushButton, QVBoxLayout,
)

from runtime import load_catalog, normalize_library_tag
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
        self.pulled_tag = None
        self.setWindowTitle(self.t("library"))
        self.resize(620, 460)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        pull_row = QHBoxLayout()
        pull_row.setSpacing(6)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.t("pull_placeholder"))
        self.search_input.setAccessibleName(self.t("pull_placeholder"))
        self.pull_button = QPushButton(self.t("pull_custom"))
        self.pull_button.setObjectName("onboardingButton")
        pull_row.addWidget(self.search_input, 1)
        pull_row.addWidget(self.pull_button)
        layout.addLayout(pull_row)

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
        row.setSpacing(6)
        self.install = QPushButton(self.t("download"))
        self.remove = QPushButton(self.t("remove_model"))
        self.stop = QPushButton(self.t("stop"))
        self.close_button = QPushButton(self.t("close"))
        for button in (self.install, self.remove, self.stop, self.close_button):
            row.addWidget(button)
        layout.addLayout(row)
        self.search_input.textChanged.connect(self.on_filter_changed)
        self.search_input.returnPressed.connect(self.pull_custom_tag)
        self.pull_button.clicked.connect(self.pull_custom_tag)
        self.listing.currentRowChanged.connect(self.select)
        self.install.clicked.connect(self.download)
        self.remove.clicked.connect(self.delete)
        self.close_button.clicked.connect(self.reject)
        self.stop.clicked.connect(self.cancel)
        self.run("catalog", lambda token, update: load_catalog())

    def tag(self):
        item = self.listing.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def on_filter_changed(self):
        current = self.tag()
        self.populate(current)
        self.select()

    def populate(self, selected=None):
        query = self.search_input.text().strip().casefold()
        self.listing.clear()
        tags = [*self.entries, *sorted(self.names.difference(self.entries))]
        shown = []
        for tag in tags:
            entry = self.entries.get(tag)
            haystack = tag.casefold()
            if entry:
                haystack += " " + entry["purpose"].get(self.t.language, "").casefold() + " " + entry["license"].casefold()
            if query and query not in haystack:
                continue
            state = self.t("installed" if tag in self.names else "available")
            size_text = f"  ({entry['size'] / 1e9:.1f} GB)" if entry else ""
            item = QListWidgetItem(f"{tag}{size_text}    ·    {state}")
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.listing.addItem(item)
            shown.append(tag)
        if shown:
            self.listing.setCurrentRow(shown.index(selected) if selected in shown else 0)

    def _valid_custom_tag(self):
        raw = self.search_input.text().strip()
        if not raw:
            return None
        try:
            return normalize_library_tag(raw)
        except ValueError:
            return None

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
            custom = self._valid_custom_tag()
            self.details.setText(
                self.t("custom_tag_hint", tag=custom) if custom else ""
            )
        idle = self.job is None
        custom = self._valid_custom_tag()
        self.pull_button.setEnabled(idle and bool(custom) and custom not in self.names)
        self.search_input.setEnabled(idle)
        self.install.setText(self.t("retry" if tag and tag == self.retry_tag else "download"))
        self.install.setEnabled(idle and bool(entry) and tag not in self.names)
        self.remove.setEnabled(idle and bool(tag) and tag in self.names)
        self.listing.setEnabled(idle)
        self.stop.setEnabled(self.operation in ("download", "pull_tag") and not idle)

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
        self.pulled_tag = entry["tag"]
        self.status.setText(self.t("downloading"))
        self.progress.setRange(0, 0)
        self.progress.show()
        self.run("download", lambda token, update: self.client.install(
            entry, token, lambda status, done, total: update((status, done, total))))

    def pull_custom_tag(self):
        if not self.job:
            try:
                target = normalize_library_tag(self.search_input.text())
            except ValueError as error:
                self.status.setText(str(error))
                return
            if target in self.entries:
                self.search_input.clear()
                self.populate(target)
                if target not in self.names:
                    self.download()
                return
            if target in self.names:
                self.search_input.clear()
                self.populate(target)
                return
            if not hasattr(self.client, "pull_tag"):
                self.status.setText(self.t("external_model"))
                return
            self.pulled_tag = target
            self.retry_tag = target
            self.status.setText(self.t("downloading"))
            self.progress.setRange(0, 0)
            self.progress.show()
            self.run("pull_tag", lambda token, update: self.client.pull_tag(
                target, token, lambda status, done, total: update((status, done, total))))

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
        if self.job and self.operation in ("download", "pull_tag"):
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
        elif self.operation in ("download", "pull_tag"):
            installed_tag = result if isinstance(result, str) and result else (self.pulled_tag or tag)
            if installed_tag:
                self.names.add(installed_tag)
                tag = installed_tag
            self.retry_tag = None
            if self.operation == "pull_tag":
                self.search_input.clear()
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
