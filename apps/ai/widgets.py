"""Shared Qt widgets. All chat, catalog and tool output is rendered as plain data."""

import html
import json
from pathlib import Path
import re
from threading import Thread

from PySide6.QtCore import QObject, Qt, Signal, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QTextBrowser

from agents import StaleFile
from history import ChatRemoved
from runtime import Cancellation, Cancelled, ContextTooLong, IntegrityError, NoSpace


class Messages:
    def __init__(self, locale_name):
        self.language = "mk" if locale_name.lower().startswith("mk") else "en"
        file = Path(__file__).with_name("locales") / (self.language + ".json")
        self.strings = json.loads(file.read_text(encoding="utf-8"))

    def __call__(self, key, **args):
        return self.strings[key].format(**args)


def label(value=""):
    widget = QLabel(value)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return widget


def confirm(window, title, message):
    box = QMessageBox(window)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.setText(message)
    yes = box.addButton(window.t("confirm"), QMessageBox.ButtonRole.AcceptRole)
    cancel = box.addButton(window.t("cancel"), QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel)
    box.exec()
    return box.clickedButton() == yes


class Work(QObject):
    """One background operation per window, delivering events on the Qt thread."""
    update = Signal(object)
    finished = Signal(object, object)

    def __init__(self, function, parent):
        super().__init__(parent)
        self.token = Cancellation()
        self.function = function

    def start(self):
        Thread(target=self.run, daemon=True).start()

    def run(self):
        try:
            result = self.function(self.token, self.update.emit)
        except Exception as error:
            self.finished.emit(None, error)
        else:
            self.finished.emit(result, None)


def error_text(t, error):
    for kind, key in ((StaleFile, "stale_file"), (ChatRemoved, "chat_removed"),
                      (Cancelled, "cancelled"), (NoSpace, "no_space"),
                      (IntegrityError, "bad_digest"), (ContextTooLong, "too_long")):
        if isinstance(error, kind):
            return t(key)
    return t("error", detail=str(error)[:700])


FENCE = re.compile(r"^```([^`\r\n]*)\r?\n(.*?)(?:^```[ \t]*(?:\r?\n|$)|\Z)", re.M | re.S)


def escaped(value):
    return html.escape(value).replace("\n", "<br>")


class Transcript(QTextBrowser):
    def __init__(self, t):
        super().__init__()
        self.t = t
        self.items = []
        self.partial = ""
        self.blocks = []
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.anchorClicked.connect(self.copy_block)
        self.setAccessibleName(t("conversation"))
        self.timer = QTimer(self, interval=60, singleShot=True)
        self.timer.timeout.connect(self.render)

    def copy_block(self, url):
        if url.scheme() == "copy" and url.path().isdecimal():
            index = int(url.path())
            if index < len(self.blocks):
                QApplication.clipboard().setText(self.blocks[index])

    def body(self, text):
        parts = []
        offset = 0
        for code in FENCE.finditer(text):
            parts.append(escaped(text[offset:code.start()]))
            index = len(self.blocks)
            self.blocks.append(code[2])
            parts.append(f'<p><small>{html.escape(code[1])} &nbsp; '
                         f'<a href="copy:{index}">{self.t("copy")}</a></small></p>'
                         f'<pre>{html.escape(code[2])}</pre>')
            offset = code.end()
        return "".join(parts) + escaped(text[offset:])

    def render(self):
        bar = self.verticalScrollBar()
        following = bar.value() >= bar.maximum() - 8
        position = bar.value()
        self.blocks = []
        content = list(self.items)
        if self.partial:
            content.append(dict(role="assistant", content=self.partial))
        parts = []
        for message in content:
            role = message["role"]
            heading = self.t(role)
            body = self.body(message["content"]) if role == "assistant" else escaped(message["content"])
            parts.append(f"<h4>{heading}</h4><div>{body}</div>")
        self.setHtml("".join(parts))
        bar.setValue(bar.maximum() if following else position)
