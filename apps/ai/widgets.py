"""Shared Qt widgets. All chat, catalog and tool output is rendered as escaped data."""

import html
import json
from pathlib import Path
import re
import time
from threading import Thread

from PySide6.QtCore import QObject, Qt, Signal, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QTextBrowser

from agents import StaleFile
from appearance import colors_for
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
INLINE_CODE = re.compile(r"`([^`\r\n]+)`")
BOLD = re.compile(r"\*\*([^\*\r\n]+)\*\*")
ITALIC = re.compile(r"(?<!\*)\*([^\*\r\n]+)\*(?!\*)")
BULLET = re.compile(r"^[ \t]*[-*][ \t]+(.*)$")
ORDERED = re.compile(r"^[ \t]*(\d+)\.[ \t]+(.*)$")
HEADING = re.compile(r"^(#{1,3})[ \t]+(.*)$")


def escaped(value):
    return html.escape(value).replace("\n", "<br>")


def _format_duration(seconds):
    if seconds < 10:
        return f"{seconds:.1f}s"
    if seconds < 60:
        return f"{round(seconds)}s"
    minutes, rem = divmod(round(seconds), 60)
    return f"{minutes}m {rem}s"


def _inline_markdown(raw_line, code_bg, code_fg):
    """Escape untrusted text first, then apply safe inline code, bold and emphasis spans."""
    chunks = []
    pos = 0
    for match in INLINE_CODE.finditer(raw_line):
        before = html.escape(raw_line[pos:match.start()])
        before = BOLD.sub(r"<b>\1</b>", before)
        before = ITALIC.sub(r"<i>\1</i>", before)
        chunks.append(before)
        code_text = html.escape(match.group(1))
        chunks.append(
            f'<span style="font-family:Consolas,\'DejaVu Sans Mono\',monospace;'
            f'background-color:{code_bg};color:{code_fg};padding:1px 4px;">{code_text}</span>'
        )
        pos = match.end()
    tail = html.escape(raw_line[pos:])
    tail = BOLD.sub(r"<b>\1</b>", tail)
    tail = ITALIC.sub(r"<i>\1</i>", tail)
    chunks.append(tail)
    return "".join(chunks)


def _prose_markdown(text, colors):
    """Format non-fenced markdown blocks safely after escaping every line."""
    if not text:
        return ""
    code_bg = colors["inset"]
    code_fg = colors["text"]
    out = []
    list_kind = None
    paragraph = []

    def flush_paragraph():
        if paragraph:
            out.append('<p style="margin:6px 0;line-height:1.56;">' + "<br>".join(paragraph) + "</p>")
            paragraph.clear()

    def close_list():
        nonlocal list_kind
        if list_kind:
            out.append(f"</{list_kind}>")
            list_kind = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            close_list()
            continue
        heading = HEADING.match(line)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            size = {1: "16px", 2: "14px", 3: "13px"}[level]
            content = _inline_markdown(heading.group(2), code_bg, code_fg)
            out.append(f'<p style="margin:10px 0 4px;font-size:{size};font-weight:600;">{content}</p>')
            continue
        bullet = BULLET.match(line)
        if bullet:
            flush_paragraph()
            if list_kind != "ul":
                close_list()
                list_kind = "ul"
                out.append('<ul style="margin:5px 0 6px 18px;">')
            out.append('<li style="margin:3px 0;line-height:1.52;">'
                       + _inline_markdown(bullet.group(1), code_bg, code_fg) + "</li>")
            continue
        ordered = ORDERED.match(line)
        if ordered:
            flush_paragraph()
            if list_kind != "ol":
                close_list()
                list_kind = "ol"
                out.append('<ol style="margin:5px 0 6px 18px;">')
            out.append('<li style="margin:3px 0;line-height:1.52;">'
                       + _inline_markdown(ordered.group(2), code_bg, code_fg) + "</li>")
            continue
        close_list()
        paragraph.append(_inline_markdown(line, code_bg, code_fg))

    flush_paragraph()
    close_list()
    return "".join(out)


class Transcript(QTextBrowser):
    def __init__(self, t):
        super().__init__()
        self.t = t
        self.theme = "light"
        self.items = []
        self.turn_meta = {}
        self.expanded_steps = set()
        self.partial = ""
        self.active_step = ""
        self.step_started = None
        self.blocks = []
        self.reply_texts = []
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.anchorClicked.connect(self.copy_block)
        self.setAccessibleName(t("conversation"))
        self.timer = QTimer(self, interval=60, singleShot=True)
        self.timer.timeout.connect(self.render)
        self.live_clock = QTimer(self, interval=250)
        self.live_clock.timeout.connect(self.render)

    def start_step(self, description):
        self.active_step = description
        if self.step_started is None:
            self.step_started = time.monotonic()
        if not self.live_clock.isActive():
            self.live_clock.start()
        self.render()

    def update_step(self, description):
        self.active_step = description
        if not self.timer.isActive():
            self.timer.start()

    def finish_step(self):
        elapsed = (time.monotonic() - self.step_started) if self.step_started is not None else 0.0
        self.live_clock.stop()
        self.active_step = ""
        self.step_started = None
        return elapsed

    def copy_block(self, url):
        scheme = url.scheme()
        path = url.path()
        if scheme == "copy" and path.isdecimal():
            index = int(path)
            if index < len(self.blocks):
                QApplication.clipboard().setText(self.blocks[index])
        elif scheme == "copymsg" and path.isdecimal():
            index = int(path)
            if index < len(self.reply_texts):
                QApplication.clipboard().setText(self.reply_texts[index])
        elif scheme == "step" and path.isdecimal():
            key = int(path)
            if key in self.expanded_steps:
                self.expanded_steps.discard(key)
            else:
                self.expanded_steps.add(key)
            self.render()

    def body(self, text, colors):
        parts = []
        offset = 0
        for code in FENCE.finditer(text):
            parts.append(_prose_markdown(text[offset:code.start()], colors))
            index = len(self.blocks)
            self.blocks.append(code[2])
            lang = html.escape(code[1].strip() or "code")
            parts.append(
                f'<table width="100%" cellspacing="0" cellpadding="0" '
                f'style="margin:8px 0;background-color:{colors["sidebar"]};border:1px solid {colors["line"]};">'
                f'<tr><td style="padding:5px 10px;border:none;background-color:{colors["inset"]};color:{colors["hint"]};'
                f'font-size:11px;">{lang} '
                f'&nbsp;&middot;&nbsp; <a href="copy:{index}" style="color:{colors["accent"]};text-decoration:none;">'
                f'{html.escape(self.t("copy"))}</a></td></tr>'
                f'<tr><td style="padding:9px 11px;border:none;">'
                f'<pre style="margin:0;font-family:Consolas,\'DejaVu Sans Mono\',monospace;font-size:12px;'
                f'color:{colors["text"]};white-space:pre-wrap;">{html.escape(code[2])}</pre>'
                f'</td></tr></table>'
            )
            offset = code.end()
        parts.append(_prose_markdown(text[offset:], colors))
        return "".join(parts)

    def _step_line(self, step_id, caption, duration_text, colors, detail_text=""):
        expanded = step_id in self.expanded_steps
        chevron = "⌄" if expanded else "›"
        time_part = f"&nbsp;&nbsp;{html.escape(duration_text)}" if duration_text else ""
        row = (
            f'<p style="margin:8px 0 4px;font-size:12px;color:{colors["hint"]};">'
            f'<a href="step:{step_id}" style="color:{colors["hint"]};text-decoration:none;">'
            f'{html.escape(caption)}{time_part}&nbsp;{chevron}</a></p>'
        )
        if expanded and detail_text:
            row += (
                f'<div style="margin:2px 0 8px 10px;padding:6px 10px;'
                f'background-color:{colors["sidebar"]};border-left:2px solid {colors["line"]};'
                f'color:{colors["muted"]};font-size:11px;">{escaped(detail_text)}</div>'
            )
        return row

    def render(self):
        colors = colors_for(self.theme)
        bar = self.verticalScrollBar()
        following = bar.value() >= bar.maximum() - 12
        position = bar.value()
        self.blocks = []
        self.reply_texts = []
        content = list(self.items)
        streaming = bool(self.partial)
        if streaming:
            content.append(dict(role="assistant", content=self.partial, _streaming=True))
        parts = [f'<div style="color:{colors["text"]};font-size:13px;">']

        pending_evidence = None
        for idx, message in enumerate(content):
            role = message["role"]
            raw = message["content"]
            if role == "user":
                pending_evidence = None
                parts.append(
                    f'<table width="100%" cellspacing="0" cellpadding="0" style="margin:12px 0 6px;">'
                    f'<tr><td width="18%"></td><td align="right">'
                    f'<table cellspacing="0" cellpadding="0" style="background-color:{colors["inset"]};'
                    f'border:1px solid {colors["line"]};">'
                    f'<tr><td style="padding:8px 13px;color:{colors["text"]};line-height:1.5;">'
                    f'{escaped(raw)}</td></tr></table></td></tr></table>'
                )
            elif role == "evidence":
                pending_evidence = (idx, raw)
            elif role == "assistant":
                is_live = bool(message.get("_streaming"))
                if is_live and self.step_started is not None:
                    live_secs = _format_duration(time.monotonic() - self.step_started)
                    caption = self.active_step or self.t("sending")
                    detail = pending_evidence[1] if pending_evidence else ""
                    parts.append(self._step_line(idx, caption, live_secs, colors, detail))
                else:
                    meta = self.turn_meta.get(idx)
                    if meta or pending_evidence:
                        step_caption = meta[0] if meta else self.t("evidence")
                        dur = _format_duration(meta[1]) if meta else ""
                        detail = pending_evidence[1] if pending_evidence else f"{step_caption} ({dur})"
                        parts.append(self._step_line(idx, step_caption, dur, colors, detail))
                pending_evidence = None
                reply_index = len(self.reply_texts)
                self.reply_texts.append(raw)
                rendered = self.body(raw, colors)
                copy_row = "" if is_live else (
                    f'<p style="margin:3px 0 12px;font-size:11px;">'
                    f'<a href="copymsg:{reply_index}" style="color:{colors["hint"]};text-decoration:none;">'
                    f'{html.escape(self.t("copy_reply"))}</a></p>'
                )
                parts.append(f'<div style="margin:2px 4px 4px;">{rendered}{copy_row}</div>')
            elif role == "note":
                parts.append(
                    f'<p style="margin:6px 4px;padding:5px 9px;background-color:{colors["sidebar"]};'
                    f'color:{colors["muted"]};font-size:12px;">{escaped(raw)}</p>'
                )

        if pending_evidence is not None:
            ev_idx, ev_raw = pending_evidence
            parts.append(self._step_line(ev_idx, self.t("evidence"), "", colors, ev_raw))

        if self.step_started is not None and not streaming:
            live_secs = _format_duration(time.monotonic() - self.step_started)
            caption = self.active_step or self.t("working")
            parts.append(
                f'<p style="margin:10px 4px;font-size:12px;color:{colors["hint"]};">'
                f'{html.escape(caption)}&nbsp;&nbsp;{html.escape(live_secs)}&nbsp;›</p>'
            )

        parts.append("</div>")
        self.setHtml("".join(parts))
        bar.setValue(bar.maximum() if following else position)
