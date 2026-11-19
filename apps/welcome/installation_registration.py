"""Explicit, reversible installation reporting. No background requests."""
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from system_info import boot_session, read_text, string_mapping

CONFIG = Path("/etc/kernova/statistics.json")
PRODUCT = Path("/usr/share/kernova/product.json")
STATE = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "kernova/installation.json"


def endpoint_url(value):
    parts = urlsplit(value)
    local = parts.scheme == "http" and parts.hostname in {"127.0.0.1", "localhost", "::1"}
    if not (parts.scheme == "https" or local) or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.path not in {"", "/"}:
        raise ValueError("Use the HTTPS address of the Kernova registration service.")
    return value.rstrip("/")


def report(endpoint, version, withdraw=False, state_path=STATE):
    endpoint = endpoint_url(endpoint)
    if boot_session(read_text(Path("/proc/cmdline"))) != "installed":
        raise ValueError("Registration is available after booting an installed Kernova system.")
    if not PRODUCT.is_file():
        raise ValueError("The Kernova product identity is unavailable.")
    state_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state["endpoint"] != endpoint:
            raise ValueError("Use the original registration service to withdraw this report.")
    else:
        if withdraw:
            return
        state = {"id": secrets.token_hex(32), "secret": secrets.token_hex(32), "endpoint": endpoint}
        descriptor, temporary = tempfile.mkstemp(dir=state_path.parent, prefix=".installation-")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(state, stream)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, state_path)
            except FileExistsError:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                if state["endpoint"] != endpoint:
                    raise ValueError("Use the original registration service.")
        finally:
            os.unlink(temporary)
    payload = {**state, "version": version, "session": "installed", "consent": True}
    payload.pop("endpoint")
    suffix = "/withdraw" if withdraw else ""
    request = Request(endpoint + "/api/installations" + suffix, data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=15) as response:
        result = json.load(response)
    if result.get("ok") is not True:
        raise ValueError("The registration service did not confirm the request.")
    # Retain credentials after withdrawal so retries remain idempotent.


def main():
    from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
    from PySide6.QtWidgets import QApplication, QCheckBox, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout

    class Signals(QObject):
        finished = Signal(str)

    class Submit(QRunnable):
        def __init__(self, endpoint, withdraw):
            super().__init__()
            self.endpoint, self.withdraw = endpoint, withdraw
            self.signals = Signals()

        def run(self):
            try:
                report(self.endpoint, string_mapping(PRODUCT).get("version", "unknown"), self.withdraw)
                message = "Your report was withdrawn." if self.withdraw else "Thank you. Your installation report was received."
            except Exception as error:
                message = "The request could not be completed. " + str(error)
            self.signals.finished.emit(message)

    app = QApplication(sys.argv)
    window = QDialog()
    window.setWindowTitle("Kernova installation reporting")
    window.resize(500, 350)
    layout = QVBoxLayout(window)
    intro = QLabel("Help Kernova understand how many installations are reported. Sharing is optional. "
                   "This sends your Kernova version, an installed-session flag and a random registration ID. "
                   "Your username, files, machine ID and hardware details are excluded. "
                   "The server receives your network address when you connect. "
                   "Reports can be withdrawn using this account.")
    intro.setWordWrap(True)
    layout.addWidget(intro)
    label = QLabel("Registration service")
    address = QLineEdit(string_mapping(CONFIG).get("endpoint", ""))
    label.setBuddy(address)
    layout.addWidget(label)
    layout.addWidget(address)
    consent = QCheckBox("I agree to send this installation report.")
    layout.addWidget(consent)
    send = QPushButton("Share my installation")
    send.setEnabled(False)
    consent.toggled.connect(send.setEnabled)
    withdraw = QPushButton("Withdraw my report")
    layout.addWidget(send)
    layout.addWidget(withdraw)
    status = QLabel("The service address will be configured when reporting is launched." if not address.text() else "")
    status.setWordWrap(True)
    layout.addWidget(status)
    tasks = []

    def submit(remove):
        send.setEnabled(False)
        withdraw.setEnabled(False)
        task = Submit(address.text(), remove)
        tasks.append(task)

        def finished(message):
            status.setText(message)
            send.setEnabled(consent.isChecked())
            withdraw.setEnabled(True)
            tasks.remove(task)
        task.signals.finished.connect(finished)
        QThreadPool.globalInstance().start(task)

    send.clicked.connect(lambda: submit(False))
    withdraw.clicked.connect(lambda: submit(True))
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
