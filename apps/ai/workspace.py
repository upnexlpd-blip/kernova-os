"""Embedded right Workspace panel, Free Ollama Agents manager, Automations and Customizations."""

import html
import os
from pathlib import Path
import re
import shutil
import sys
import time

from PySide6.QtCore import QProcess, QProcessEnvironment, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFontDatabase
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMenu, QPlainTextEdit, QProgressBar, QPushButton,
    QStackedWidget, QTextBrowser, QToolButton, QVBoxLayout, QWidget,
)

from appearance import colors_for, icon
from runtime import _open_https, _read_limited, normalize_library_tag
from widgets import Work, error_text, label


PERSONAS = (
    ("default", "persona_default", ""),
    ("architect", "persona_architect",
     " Act as a senior software architect: structure explanations clearly, highlight edge cases and keep code modular."),
    ("doctor", "persona_doctor",
     " Act as a Linux/Debian system specialist: prioritize safe diagnostics, clear verification commands and reversible steps."),
    ("reviewer", "persona_reviewer",
     " Act as a code & security reviewer: identify bugs, race conditions, input validation gaps and concrete fixes."),
    ("tester", "persona_tester",
     " Act as a QA & test engineer: propose high-value unit, integration and edge-case tests with clear assertions."),
)

CLI_AGENTS = (
    {
        "id": "aider",
        "name": "Aider (Ollama Pair Programmer)",
        "binary": "aider",
        "license": "Apache-2.0",
        "guide": "https://aider.chat/docs/llms/ollama.html",
        "linux_install": ("https://aider.chat/install.sh", "/bin/sh"),
        "win_pip": "aider-chat",
        "desc_en": "Free open-source terminal coding agent with Git diffs, connected directly to local Ollama.",
        "desc_mk": "Бесплатен терминалски кодинг агент со Git разлики, поврзан директно со локалниот Ollama.",
        "run_cmd": lambda exe, model: f'"{exe}" --model ollama_chat/{model or "qwen2.5-coder:7b"}',
    },
    {
        "id": "opencode",
        "name": "OpenCode CLI",
        "binary": "opencode",
        "license": "MIT",
        "guide": "https://opencode.ai",
        "linux_install": ("https://opencode.ai/install", "/bin/bash"),
        "win_npm": "opencode-ai",
        "desc_en": "Free open-source interactive coding agent in your terminal supporting local Ollama models.",
        "desc_mk": "Бесплатен интерактивен кодинг агент во терминал со поддршка за локални Ollama модели.",
        "run_cmd": lambda exe, model: f'"{exe}"',
    },
    {
        "id": "goose",
        "name": "Goose Developer Agent",
        "binary": "goose",
        "license": "Apache-2.0",
        "guide": "https://block.github.io/goose/",
        "linux_install": ("https://github.com/block/goose/releases/download/stable/download_cli.sh", "/bin/bash"),
        "win_pip": "",
        "desc_en": "Autonomous open-source local developer agent by Block, configurable with local Ollama.",
        "desc_mk": "Автономен бесплатен локален девелоперски агент со поддршка за локален Ollama.",
        "run_cmd": lambda exe, model: f'"{exe}" session',
    },
)

QUICK_MODELS = (
    "llama3.2:3b",
    "deepseek-r1:7b",
    "gemma3:4b",
    "qwen2.5-coder:7b",
    "mistral:7b",
)

LINUX_AGENT_INSTALL = """set -eu
if [ "$(id -u)" -eq 0 ]; then
    printf '%s\\n' "$1" >&2
    exit 1
fi
shift
url=$1
interpreter=$2
installer=$(mktemp)
trap 'rm -f -- "$installer"' 0
trap 'exit 130' INT
trap 'exit 143' TERM
/usr/bin/curl -q --fail --show-error --silent --location --proto '=https' --proto-redir '=https' \\
    --connect-timeout 15 --max-time 120 --output "$installer" "$url"
"$interpreter" "$installer"
"""


def find_agent_executable(binary_name):
    home = Path.home()
    candidates = [
        home / ".local" / "bin" / binary_name,
        home / ".opencode" / "bin" / binary_name,
        home / "AppData" / "Roaming" / "Python" / "Scripts" / f"{binary_name}.exe",
        home / "AppData" / "Roaming" / "npm" / f"{binary_name}.cmd",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return shutil.which(binary_name)


def _strip_tags_to_readable_html(raw_bytes, url):
    text = raw_bytes.decode("utf-8", errors="replace")
    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    title = html.unescape(title_match.group(1)).strip() if title_match else url
    cleaned = re.sub(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", "", text, flags=re.I | re.S)
    cleaned = re.sub(r"<(br|p|div|li|tr|h[1-6])[^>]*>", "\n", cleaned, flags=re.I)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    lines = [" ".join(line.split()) for line in cleaned.splitlines()]
    body = "\n".join(line for line in lines if line)[:24000]
    return title[:140], body or "(Empty page)"


class WorkspacePane(QWidget):
    """Right-side workspace panel matching Antigravity: Search/URL, Review, Open File, Terminal, Browser, Side Question, Plugins."""

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.t = owner.t
        self.setObjectName("workspacePane")
        self.setMinimumWidth(265)
        self.expanded = False
        self.side_job = None
        self.pull_job = None
        self.browser_job = None
        self.side_output = ""
        self.side_started = None
        self.active_agent_install = None
        self.icon_refs = []

        self.term_proc = QProcess(self)
        self.term_proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.term_proc.readyReadStandardOutput.connect(self._on_term_output)
        self.term_proc.finished.connect(self._on_term_finished)

        self.agent_proc = QProcess(self)
        self.agent_proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.agent_proc.readyReadStandardOutput.connect(self._on_agent_output)
        self.agent_proc.finished.connect(self._on_agent_finished)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 10)
        root.setSpacing(6)

        # Sub-navigation bar when inside a tool
        self.sub_bar = QWidget()
        sub = QHBoxLayout(self.sub_bar)
        sub.setContentsMargins(0, 0, 0, 2)
        sub.setSpacing(4)
        self.home_btn = self._icon_btn("arrow_left", "back", self.show_home)
        self.pane_title = QLabel("")
        self.pane_title.setObjectName("paneTitle")
        sub.addWidget(self.home_btn)
        sub.addWidget(self.pane_title, 1)
        self.sub_bar.hide()
        root.addWidget(self.sub_bar)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self._build_home()
        self._build_review()
        self._build_open_file()
        self._build_terminal()
        self._build_browser()
        self._build_side_question()
        self._build_plugins()

    def _icon_btn(self, symbol, tip_key, callback, obj_name="iconNav"):
        btn = QPushButton("")
        btn.setObjectName(obj_name)
        btn.setToolTip(self.t(tip_key))
        btn.setAccessibleName(self.t(tip_key))
        btn.setIconSize(QSize(15, 15))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        self.icon_refs.append((btn, symbol))
        return btn

    def _build_home(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(12, 24, 12, 12)
        outer.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setSpacing(4)
        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("pillSearch")
        self.search_bar.setPlaceholderText(self.t("search_or_url"))
        self.search_bar.setAccessibleName(self.t("search_or_url"))
        self.search_bar.textChanged.connect(self._filter_home)
        self.search_bar.returnPressed.connect(self._submit_search_or_url)
        self.more_btn = QToolButton()
        self.more_btn.setObjectName("iconNav")
        self.more_btn.setToolTip(self.t("workspace"))
        self.more_btn.setIconSize(QSize(15, 15))
        self.more_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.icon_refs.append((self.more_btn, "more"))
        more_menu = QMenu(self.more_btn)
        more_menu.addAction(self.t("ws_review"), lambda: self.open_section("review"))
        more_menu.addAction(self.t("ws_open_file"), lambda: self.open_section("file"))
        more_menu.addAction(self.t("ws_terminal"), lambda: self.open_section("terminal"))
        more_menu.addAction(self.t("ws_browser"), lambda: self.open_section("browser"))
        more_menu.addAction(self.t("ws_side_question"), lambda: self.open_section("side"))
        more_menu.addAction(self.t("ws_plugins"), lambda: self.open_section("plugins"))
        self.more_btn.setMenu(more_menu)
        search_row.addWidget(self.search_bar, 1)
        search_row.addWidget(self.more_btn)
        outer.addLayout(search_row)
        outer.addSpacing(4)

        self.home_buttons = []
        items = (
            ("review", "ws_review", "review", False),
            ("file", "ws_open_file", "file", False),
            ("terminal", "ws_terminal", "terminal", False),
            ("browser", "ws_browser", "globe", False),
            ("side", "ws_side_question", "side_chat", False),
            ("plugins", "ws_plugins", "plugin", True),
        )
        for section_id, key, sym, has_arrow in items:
            caption = self.t(key) + ("   ›" if has_arrow else "")
            btn = QPushButton(caption)
            btn.setObjectName("workspaceItem")
            btn.setAccessibleName(self.t(key))
            btn.setIconSize(QSize(15, 15))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, sid=section_id: self.open_section(sid))
            self.icon_refs.append((btn, sym))
            self.home_buttons.append((section_id, self.t(key), btn))
            outer.addWidget(btn)

        outer.addStretch(1)
        self.stack.addWidget(page)

    def _build_review(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(6)
        self.review_info = label(self.t("review_empty"))
        lay.addWidget(self.review_info)
        row = QHBoxLayout()
        pick_folder = QPushButton(self.t("project"))
        pick_folder.clicked.connect(self.owner.open_project)
        propose_btn = QPushButton(self.t("edit"))
        propose_btn.clicked.connect(self._toggle_propose_from_review)
        row.addWidget(pick_folder)
        row.addWidget(propose_btn)
        lay.addLayout(row)
        self.diff_view = QPlainTextEdit()
        self.diff_view.setObjectName("codePreview")
        self.diff_view.setReadOnly(True)
        self.diff_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.diff_view.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.diff_view.setPlaceholderText(self.t("review_empty"))
        lay.addWidget(self.diff_view, 1)
        self.stack.addWidget(page)

    def _build_open_file(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(6)
        top = QHBoxLayout()
        self.file_filter = QLineEdit()
        self.file_filter.setPlaceholderText(self.t("filter_files"))
        self.file_filter.textChanged.connect(self.refresh_files)
        choose_btn = QPushButton(self.t("project"))
        choose_btn.clicked.connect(self.owner.choose_project)
        top.addWidget(self.file_filter, 1)
        top.addWidget(choose_btn)
        lay.addLayout(top)
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(150)
        self.file_list.currentItemChanged.connect(self._preview_selected_file)
        lay.addWidget(self.file_list)
        self.file_preview = QPlainTextEdit()
        self.file_preview.setObjectName("codePreview")
        self.file_preview.setReadOnly(True)
        self.file_preview.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.file_preview.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        lay.addWidget(self.file_preview, 1)
        attach_btn = QPushButton(self.t("attach_file"))
        attach_btn.setObjectName("onboardingButton")
        attach_btn.clicked.connect(self._attach_selected_file)
        lay.addWidget(attach_btn)
        self.stack.addWidget(page)

    def _build_terminal(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(6)
        self.term_cwd_label = QLabel("")
        self.term_cwd_label.setObjectName("inlineStatus")
        lay.addWidget(self.term_cwd_label)
        self.term_output = QPlainTextEdit()
        self.term_output.setObjectName("terminalView")
        self.term_output.setReadOnly(True)
        self.term_output.setMaximumBlockCount(1000)
        self.term_output.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.term_output.setPlaceholderText(self.t("terminal_hint"))
        lay.addWidget(self.term_output, 1)
        cmd_row = QHBoxLayout()
        cmd_row.setSpacing(4)
        self.term_input = QLineEdit()
        self.term_input.setPlaceholderText(self.t("terminal_prompt"))
        self.term_input.returnPressed.connect(self.run_terminal_command)
        self.term_run_btn = QPushButton(self.t("run_cmd"))
        self.term_run_btn.clicked.connect(self.run_terminal_command)
        self.term_stop_btn = QPushButton(self.t("stop"))
        self.term_stop_btn.clicked.connect(self.stop_terminal_command)
        self.term_stop_btn.setEnabled(False)
        clear_btn = QPushButton(self.t("clear"))
        clear_btn.clicked.connect(self.term_output.clear)
        cmd_row.addWidget(self.term_input, 1)
        cmd_row.addWidget(self.term_run_btn)
        cmd_row.addWidget(self.term_stop_btn)
        cmd_row.addWidget(clear_btn)
        lay.addLayout(cmd_row)
        self.stack.addWidget(page)

    def _build_browser(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(6)
        nav = QHBoxLayout()
        nav.setSpacing(4)
        self.url_input = QLineEdit("https://ollama.com/library")
        self.url_input.setPlaceholderText("https://...")
        self.url_input.returnPressed.connect(self.open_browser_url)
        go_btn = QPushButton(self.t("go"))
        go_btn.clicked.connect(self.open_browser_url)
        ext_btn = QPushButton(self.t("open_external"))
        ext_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.url_input.text().strip())))
        nav.addWidget(self.url_input, 1)
        nav.addWidget(go_btn)
        nav.addWidget(ext_btn)
        lay.addLayout(nav)
        self.browser_status = QLabel("")
        self.browser_status.setObjectName("inlineStatus")
        lay.addWidget(self.browser_status)
        self.browser_view = QPlainTextEdit()
        self.browser_view.setObjectName("codePreview")
        self.browser_view.setReadOnly(True)
        self.browser_view.setPlaceholderText(self.t("browser_hint"))
        lay.addWidget(self.browser_view, 1)
        self.stack.addWidget(page)

    def _build_side_question(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(6)
        self.side_status = QLabel(self.t("side_hint"))
        self.side_status.setObjectName("inlineStatus")
        self.side_status.setWordWrap(True)
        lay.addWidget(self.side_status)
        self.side_view = QTextBrowser()
        self.side_view.setOpenLinks(False)
        self.side_view.setOpenExternalLinks(False)
        lay.addWidget(self.side_view, 1)
        row = QHBoxLayout()
        row.setSpacing(4)
        self.side_input = QLineEdit()
        self.side_input.setPlaceholderText(self.t("side_placeholder"))
        self.side_input.returnPressed.connect(self.ask_side_question)
        self.side_send = QPushButton(self.t("send"))
        self.side_send.setObjectName("onboardingButton")
        self.side_send.clicked.connect(self.ask_side_question)
        self.side_stop = QPushButton(self.t("stop"))
        self.side_stop.clicked.connect(self.stop_side_question)
        self.side_stop.hide()
        row.addWidget(self.side_input, 1)
        row.addWidget(self.side_send)
        row.addWidget(self.side_stop)
        lay.addLayout(row)
        self.stack.addWidget(page)

    def _build_plugins(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(6)

        # 1. Built-in Local Ollama Agent Persona
        lay.addWidget(QLabel(self.t("builtin_agents")))
        persona_row = QHBoxLayout()
        self.persona_combo = QComboBox()
        for pid, key, _ in PERSONAS:
            self.persona_combo.addItem(self.t(key), pid)
        self.persona_combo.currentIndexChanged.connect(self._persona_selected)
        persona_row.addWidget(self.persona_combo, 1)
        lay.addLayout(persona_row)

        # 2. Quick Free Ollama Models Pull
        lay.addWidget(QLabel(self.t("free_ollama_models")))
        quick_row = QHBoxLayout()
        quick_row.setSpacing(4)
        self.quick_model_combo = QComboBox()
        for mtag in QUICK_MODELS:
            self.quick_model_combo.addItem(mtag, mtag)
        self.quick_pull_btn = QPushButton(self.t("download"))
        self.quick_pull_btn.setObjectName("onboardingButton")
        self.quick_pull_btn.clicked.connect(self._pull_selected_quick_model)
        lib_btn = QPushButton(self.t("library"))
        lib_btn.clicked.connect(self.owner.open_library)
        quick_row.addWidget(self.quick_model_combo, 1)
        quick_row.addWidget(self.quick_pull_btn)
        quick_row.addWidget(lib_btn)
        lay.addLayout(quick_row)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(4)
        self.custom_tag_edit = QLineEdit()
        self.custom_tag_edit.setPlaceholderText(self.t("pull_placeholder"))
        self.custom_tag_edit.returnPressed.connect(self._pull_typed_model)
        pull_typed = QPushButton(self.t("pull_custom"))
        pull_typed.clicked.connect(self._pull_typed_model)
        custom_row.addWidget(self.custom_tag_edit, 1)
        custom_row.addWidget(pull_typed)
        lay.addLayout(custom_row)

        self.pull_progress = QProgressBar()
        self.pull_progress.hide()
        lay.addWidget(self.pull_progress)

        # 3. Free Open-Source Ollama CLI Agents
        lay.addWidget(QLabel(self.t("free_cli_agents")))
        self.agent_list = QListWidget()
        self.agent_list.setMaximumHeight(96)
        self.agent_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.agent_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.agent_list.currentRowChanged.connect(self._refresh_agent_buttons)
        lay.addWidget(self.agent_list)
        self.agent_desc = label()
        lay.addWidget(self.agent_desc)

        agent_btns = QHBoxLayout()
        agent_btns.setSpacing(4)
        self.agent_install_btn = QPushButton(self.t("install_agent"))
        self.agent_install_btn.clicked.connect(self._install_or_run_cli_agent)
        self.agent_guide_btn = QPushButton(self.t("guide_btn"))
        self.agent_guide_btn.clicked.connect(self._open_agent_guide)
        self.agent_stop_btn = QPushButton(self.t("stop"))
        self.agent_stop_btn.clicked.connect(self._stop_agent_install)
        self.agent_stop_btn.setEnabled(False)
        agent_btns.addWidget(self.agent_install_btn)
        agent_btns.addWidget(self.agent_guide_btn)
        agent_btns.addWidget(self.agent_stop_btn)
        lay.addLayout(agent_btns)

        self.plugin_log = QPlainTextEdit()
        self.plugin_log.setObjectName("terminalView")
        self.plugin_log.setReadOnly(True)
        self.plugin_log.setMaximumHeight(95)
        self.plugin_log.setPlaceholderText(self.t("agent_log_hint"))
        lay.addWidget(self.plugin_log)
        lay.addStretch(1)

        self.stack.addWidget(page)

    def recolor(self, theme):
        for widget, sym in self.icon_refs:
            widget.setIcon(icon(sym, theme))

    def show_home(self):
        self.stack.setCurrentIndex(0)
        self.sub_bar.hide()

    def open_section(self, name):
        mapping = {
            "review": (1, "ws_review"),
            "file": (2, "ws_open_file"),
            "terminal": (3, "ws_terminal"),
            "browser": (4, "ws_browser"),
            "side": (5, "ws_side_question"),
            "plugins": (6, "ws_plugins"),
        }
        idx, key = mapping[name]
        self.pane_title.setText(self.t(key))
        self.sub_bar.show()
        self.stack.setCurrentIndex(idx)
        self.setVisible(True)
        if name == "file":
            self.refresh_files()
        elif name == "terminal":
            self._update_terminal_cwd()
        elif name == "plugins":
            self.refresh_plugins()
        elif name == "review":
            self.refresh_review()

    def _filter_home(self, text):
        q = text.strip().casefold()
        for _, title, btn in self.home_buttons:
            btn.setVisible(not q or q in title.casefold())

    def _submit_search_or_url(self):
        raw = self.search_bar.text().strip()
        if not raw:
            return
        if raw.startswith(("https://", "http://")) or ("." in raw and " " not in raw):
            url = raw if raw.startswith(("https://", "http://")) else "https://" + raw
            self.url_input.setText(url)
            self.open_section("browser")
            self.open_browser_url()
            return
        for sid, title, _ in self.home_buttons:
            if raw.casefold() in title.casefold():
                self.open_section(sid)
                return
        self.side_input.setText(raw)
        self.open_section("side")
        self.ask_side_question()

    def _toggle_propose_from_review(self):
        self.owner.mode.setCurrentText("Code")
        if self.owner.files.currentData() is not None:
            self.owner.edit.setChecked(not self.owner.edit.isChecked())
        self.owner.controls()

    def set_last_diff(self, path, diff_text):
        if diff_text:
            self.review_info.setText(f"{path}")
            self.diff_view.setPlainText(diff_text)
        else:
            self.review_info.setText(self.t("unchanged"))
            self.diff_view.clear()

    def refresh_review(self):
        if not self.diff_view.toPlainText().strip():
            proj = str(self.owner.project.root) if self.owner.project else self.t("no_file")
            self.review_info.setText(f"{self.t('review_empty')} ({proj})")

    def refresh_files(self):
        self.file_list.clear()
        if not self.owner.project:
            return
        q = self.file_filter.text().strip().casefold()
        for rel in self.owner.project.list_files():
            if not q or q in rel.casefold():
                item = QListWidgetItem(rel)
                item.setData(Qt.ItemDataRole.UserRole, rel)
                self.file_list.addItem(item)
        if self.file_list.count():
            self.file_list.setCurrentRow(0)

    def _preview_selected_file(self, item):
        if not item or not self.owner.project:
            self.file_preview.clear()
            return
        rel = item.data(Qt.ItemDataRole.UserRole)
        try:
            snap = self.owner.project.read(rel)
            self.file_preview.setPlainText(snap.text)
        except (OSError, ValueError) as error:
            self.file_preview.setPlainText(str(error))

    def _attach_selected_file(self):
        item = self.file_list.currentItem()
        if item and self.owner.project:
            rel = item.data(Qt.ItemDataRole.UserRole)
            self.owner.mode.setCurrentText("Code")
            idx = self.owner.files.findData(rel)
            if idx >= 0:
                self.owner.files.setCurrentIndex(idx)
            self.owner.update_context_chips()
            self.owner.prompt.setFocus()

    def _working_dir(self):
        if self.owner.project and self.owner.project.root.is_dir():
            return str(self.owner.project.root)
        return str(Path.home())

    def _update_terminal_cwd(self):
        self.term_cwd_label.setText(f"cwd: {self._working_dir()}")

    def run_terminal_command(self, command_override=None):
        if self.term_proc.state() != QProcess.ProcessState.NotRunning:
            return
        cmd = (command_override if isinstance(command_override, str) else self.term_input.text()).strip()
        if not cmd:
            return
        if not isinstance(command_override, str):
            self.term_input.clear()
        cwd = self._working_dir()
        self._update_terminal_cwd()
        self.term_output.appendPlainText(f"$ {cmd}")
        self.term_proc.setWorkingDirectory(cwd)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("OLLAMA_API_BASE", "http://127.0.0.1:11434")
        env.insert("OLLAMA_HOST", "127.0.0.1:11434")
        self.term_proc.setProcessEnvironment(env)
        self.term_run_btn.setEnabled(False)
        self.term_stop_btn.setEnabled(True)
        if os.name == "nt":
            self.term_proc.start("cmd.exe", ["/d", "/s", "/c", cmd])
        else:
            self.term_proc.start("/bin/sh", ["-c", cmd])
        self.term_proc.closeWriteChannel()

    def stop_terminal_command(self):
        if self.term_proc.state() != QProcess.ProcessState.NotRunning:
            self.term_proc.kill()

    def _on_term_output(self):
        data = bytes(self.term_proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            self.term_output.insertPlainText(data.replace("\r\n", "\n"))
            self.term_output.ensureCursorVisible()

    def _on_term_finished(self, code, _status):
        self._on_term_output()
        self.term_output.appendPlainText(f"[exit {code}]\n")
        self.term_run_btn.setEnabled(True)
        self.term_stop_btn.setEnabled(False)

    def open_browser_url(self):
        if self.browser_job is not None:
            return
        url = self.url_input.text().strip()
        if not url:
            return
        if not url.startswith(("https://", "http://")):
            url = "https://" + url
            self.url_input.setText(url)
        if not url.startswith("https://"):
            self.browser_status.setText(self.t("https_only"))
            return
        self.browser_status.setText(self.t("loading"))

        def fetch(_token, _update):
            with _open_https(url) as stream:
                raw = _read_limited(stream, 512 * 1024)
            return _strip_tags_to_readable_html(raw, url)

        self.browser_job = Work(fetch, self)
        self.browser_job.finished.connect(self._on_browser_done)
        self.browser_job.start()

    def _on_browser_done(self, result, error):
        self.browser_job.deleteLater()
        self.browser_job = None
        if error:
            self.browser_status.setText(error_text(self.t, error))
        else:
            title, content = result
            self.browser_status.setText(title)
            self.browser_view.setPlainText(content)

    def ask_side_question(self):
        if self.side_job is not None:
            return
        question = self.side_input.text().strip()
        model = self.owner.models.currentText()
        if not question or not model or self.owner.state != "ready":
            self.side_status.setText(self.t("empty" if not model else "side_hint"))
            return
        self.side_input.clear()
        self.side_output = ""
        self.side_started = time.monotonic()
        self.side_send.hide()
        self.side_stop.show()
        self.side_status.setText(self.t("working"))

        def run(token, update):
            messages = [
                dict(role="system", content="You are KERNOVA AI Side Question. Give a concise, direct helpful answer."),
                dict(role="user", content=question),
            ]
            self.owner.client.chat(model, messages, token, update)
            return question

        self.side_job = Work(run, self)
        self.side_job.update.connect(self._on_side_chunk)
        self.side_job.finished.connect(self._on_side_done)
        self._side_question_text = question
        self.side_job.start()

    def _on_side_chunk(self, chunk):
        self.side_output += chunk
        elapsed = time.monotonic() - (self.side_started or time.monotonic())
        self.side_status.setText(f"{self.t('sending')}  {elapsed:.1f}s ›")
        colors = colors_for(self.owner.theme)
        self.side_view.setHtml(
            f'<p style="color:{colors["hint"]};font-size:11px;"><b>{html.escape(self._side_question_text)}</b></p>'
            f'<div style="color:{colors["text"]};line-height:1.5;">'
            f'{html.escape(self.side_output).replace(chr(10), "<br>")}</div>'
        )

    def stop_side_question(self):
        if self.side_job:
            self.side_job.token.cancel()

    def _on_side_done(self, _result, error):
        elapsed = time.monotonic() - (self.side_started or time.monotonic())
        self.side_job.deleteLater()
        self.side_job = None
        self.side_stop.hide()
        self.side_send.show()
        if error:
            self.side_status.setText(error_text(self.t, error))
        else:
            self.side_status.setText(f"{self.t('completed_in', seconds=f'{elapsed:.1f}s')} ›")

    def _persona_selected(self):
        pid = self.persona_combo.currentData() or "default"
        self.owner.set_persona(pid)

    def refresh_plugins(self):
        row = max(0, self.agent_list.currentRow())
        self.agent_list.clear()
        for spec in CLI_AGENTS:
            exe = find_agent_executable(spec["binary"])
            state = self.t("installed") if exe else self.t("available")
            item = QListWidgetItem(f"{spec['name']}   ·   {state}")
            item.setData(Qt.ItemDataRole.UserRole, spec["id"])
            self.agent_list.addItem(item)
        if self.agent_list.count():
            self.agent_list.setCurrentRow(min(row, self.agent_list.count() - 1))
        self._refresh_agent_buttons()

    def _current_agent_spec(self):
        idx = self.agent_list.currentRow()
        return CLI_AGENTS[idx] if 0 <= idx < len(CLI_AGENTS) else None

    def _refresh_agent_buttons(self):
        spec = self._current_agent_spec()
        busy = self.agent_proc.state() != QProcess.ProcessState.NotRunning
        if not spec:
            self.agent_desc.clear()
            self.agent_install_btn.setEnabled(False)
            return
        desc = spec["desc_mk"] if self.t.language == "mk" else spec["desc_en"]
        self.agent_desc.setText(f"{desc}\n{self.t('license_label')}: {spec['license']}")
        exe = find_agent_executable(spec["binary"])
        self.agent_install_btn.setText(self.t("run_agent" if exe else "install_agent"))
        self.agent_install_btn.setEnabled(not busy)
        self.agent_stop_btn.setEnabled(busy)

    def _open_agent_guide(self):
        spec = self._current_agent_spec()
        if spec:
            QDesktopServices.openUrl(QUrl(spec["guide"]))

    def _install_or_run_cli_agent(self):
        spec = self._current_agent_spec()
        if not spec or self.agent_proc.state() != QProcess.ProcessState.NotRunning:
            return
        exe = find_agent_executable(spec["binary"])
        if exe:
            cmd = spec["run_cmd"](exe, self.owner.models.currentText())
            self.open_section("terminal")
            self.run_terminal_command(cmd)
            return
        self.active_agent_install = spec["name"]
        self.plugin_log.clear()
        self.plugin_log.appendPlainText(f"Installing {spec['name']}...")
        self._refresh_agent_buttons()
        if os.name != "nt" and Path("/usr/bin/curl").is_file():
            url, interp = spec["linux_install"]
            self.agent_proc.start("/bin/sh", ["-c", LINUX_AGENT_INSTALL, "kernova-ai", self.t("root"), url, interp])
            self.agent_proc.closeWriteChannel()
            self._refresh_agent_buttons()
            return
        if os.name == "nt" and spec.get("win_pip"):
            self.agent_proc.start(sys.executable, ["-m", "pip", "install", "--user", spec["win_pip"]])
            self.agent_proc.closeWriteChannel()
            self._refresh_agent_buttons()
            return
        if os.name == "nt" and spec.get("win_npm") and shutil.which("npm"):
            self.agent_proc.start("cmd.exe", ["/d", "/s", "/c", f"npm install -g {spec['win_npm']}"])
            self.agent_proc.closeWriteChannel()
            self._refresh_agent_buttons()
            return
        QDesktopServices.openUrl(QUrl(spec["guide"]))
        self.plugin_log.appendPlainText(spec["guide"])

    def _on_agent_output(self):
        data = bytes(self.agent_proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            self.plugin_log.insertPlainText(data.replace("\r\n", "\n"))
            self.plugin_log.ensureCursorVisible()

    def _stop_agent_install(self):
        if self.agent_proc.state() != QProcess.ProcessState.NotRunning:
            self.agent_proc.kill()

    def _on_agent_finished(self, code, _status):
        self._on_agent_output()
        self.plugin_log.appendPlainText(f"[exit {code}]")
        self.active_agent_install = None
        self.refresh_plugins()

    def _pull_selected_quick_model(self):
        self._start_model_pull(self.quick_model_combo.currentData())

    def _pull_typed_model(self):
        raw = self.custom_tag_edit.text().strip()
        if raw:
            self._start_model_pull(raw)

    def _start_model_pull(self, raw_tag):
        if self.pull_job is not None:
            return
        try:
            tag = normalize_library_tag(raw_tag)
        except ValueError as error:
            self.plugin_log.setPlainText(str(error))
            return
        if not hasattr(self.owner.client, "pull_tag"):
            self.owner.open_library()
            return
        self.pull_progress.setRange(0, 0)
        self.pull_progress.show()
        self.quick_pull_btn.setEnabled(False)
        self.plugin_log.setPlainText(f"{self.t('downloading')} {tag}...")

        def pull(token, update):
            return self.owner.client.pull_tag(tag, token, lambda st, done, tot: update((tag, st, done, tot)))

        self.pull_job = Work(pull, self)
        self.pull_job.update.connect(self._on_pull_progress)
        self.pull_job.finished.connect(self._on_pull_done)
        self.pull_job.start()

    def _on_pull_progress(self, info):
        tag, status, done, total = info
        if total > 0:
            self.pull_progress.setRange(0, 100)
            self.pull_progress.setValue(min(100, int(done * 100 / total)))
            self.plugin_log.setPlainText(f"{tag}: {status} ({done / 1e6:.0f} / {total / 1e6:.0f} MB)")
        else:
            self.pull_progress.setRange(0, 0)
            self.plugin_log.setPlainText(f"{tag}: {status}")

    def _on_pull_done(self, result, error):
        self.pull_job.deleteLater()
        self.pull_job = None
        self.pull_progress.hide()
        self.quick_pull_btn.setEnabled(True)
        if error:
            self.plugin_log.setPlainText(error_text(self.t, error))
        else:
            self.custom_tag_edit.clear()
            self.plugin_log.setPlainText(self.t("downloaded", tag=result))
            self.owner.settings.setValue("model", result)
            self.owner.probe()

    def shutdown(self):
        for job in (self.side_job, self.pull_job, self.browser_job):
            if job is not None:
                job.token.cancel()
        for proc in (self.term_proc, self.agent_proc):
            if proc.state() != QProcess.ProcessState.NotRunning:
                proc.kill()
                proc.waitForFinished(500)


class AutomationsDialog(QDialog):
    """Quick local diagnostic and developer workflows."""

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        t = owner.t
        self.setWindowTitle(t("automations"))
        self.resize(460, 340)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)
        lay.addWidget(label(t("automations_desc")))

        self.items = QListWidget()
        presets = [
            (t("free_disk"), "disk"),
            (t("check_system"), "system"),
            (t("auto_plan_audit"), "plan"),
            (t("auto_test_suite"), "test"),
        ]
        for text, action_id in presets:
            it = QListWidgetItem(text)
            it.setData(Qt.ItemDataRole.UserRole, action_id)
            self.items.addItem(it)
        self.items.setCurrentRow(0)
        lay.addWidget(self.items, 1)

        row = QHBoxLayout()
        row.addStretch()
        close_btn = QPushButton(t("close"))
        close_btn.clicked.connect(self.reject)
        run_btn = QPushButton(t("run_cmd"))
        run_btn.setObjectName("onboardingButton")
        run_btn.clicked.connect(self._run_selected)
        row.addWidget(close_btn)
        row.addWidget(run_btn)
        lay.addLayout(row)

    def _run_selected(self):
        item = self.items.currentItem()
        if not item:
            return
        code = item.data(Qt.ItemDataRole.UserRole)
        self.accept()
        if code == "disk":
            self.owner.quick_check(True)
        elif code == "system":
            self.owner.quick_check(False)
        elif code == "plan":
            self.owner.apply_quick_intent("plan")
        elif code == "test":
            self.owner.apply_quick_intent("test")


class CustomizationsDialog(QDialog):
    """Custom system prompt, active persona and shortcuts to Free Ollama Agents & Models."""

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        t = owner.t
        self.setWindowTitle(t("customizations"))
        self.resize(480, 360)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)
        lay.addWidget(QLabel(t("custom_instructions")))
        self.instructions = QPlainTextEdit()
        self.instructions.setPlaceholderText(t("custom_instructions_hint"))
        self.instructions.setPlainText(owner.custom_instructions)
        lay.addWidget(self.instructions, 1)

        shortcuts = QHBoxLayout()
        models_btn = QPushButton(t("library"))
        models_btn.clicked.connect(lambda: (self.accept(), owner.open_library()))
        agents_btn = QPushButton(t("ws_plugins"))
        agents_btn.clicked.connect(lambda: (self.accept(), owner.workspace_pane.open_section("plugins")))
        shortcuts.addWidget(models_btn)
        shortcuts.addWidget(agents_btn)
        shortcuts.addStretch()
        lay.addLayout(shortcuts)

        footer = QHBoxLayout()
        footer.addStretch()
        cancel = QPushButton(t("cancel"))
        cancel.clicked.connect(self.reject)
        save = QPushButton(t("save"))
        save.setObjectName("onboardingButton")
        save.clicked.connect(self._save)
        footer.addWidget(cancel)
        footer.addWidget(save)
        lay.addLayout(footer)

    def _save(self):
        text = self.instructions.toPlainText().strip()[:1500]
        self.owner.custom_instructions = text
        self.owner.settings.setValue("custom_instructions", text)
        self.accept()
