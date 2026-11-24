"""Local, user-scoped Support and Code tools. Model output is always data."""
from contextlib import ExitStack, contextmanager, suppress
from dataclasses import dataclass
from difflib import unified_diff
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import sys
import unicodedata


def _label(language, english, macedonian):
    return macedonian if language.startswith("mk") else english


def _clean(value, limit):
    return "".join(c for c in str(value)[:limit] if c.isprintable())


def _command(args):
    return subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=5, check=True).stdout


@dataclass(frozen=True)
class DiskUsage:
    path: str
    total: int
    used: int
    free: int


def _volumes():
    volumes = {}
    for path in (Path.home().anchor, Path.home()):
        key = os.stat(path).st_dev
        if key in volumes:
            continue
        total, used, free = shutil.disk_usage(path)
        if total <= 0 or not 0 <= free <= total or not 0 <= used <= total:
            raise ValueError("Invalid filesystem counters.")
        volumes[key] = DiskUsage(str(path), total, used, free)
    return list(volumes.values())


def _disk_evidence(volumes, language):
    return "\n".join(f"{v.path} — {v.used / 2**30:.1f} / {v.total / 2**30:.1f} GiB "
                     f"({v.used / v.total:.1%}), {v.free / 2**30:.1f} GiB "
                     + _label(language, "available", "слободни") for v in volumes)


def _low_space(volume):
    return volume.free * 20 < volume.total or volume.free < 2**30


def _disk_status(volume, language):
    if volume.free == 0:
        return _label(language, "The filesystem reports zero bytes available to your account.",
                      "Датотечниот систем пријавува нула достапни бајти за вашата сметка.")
    if _low_space(volume):
        return _label(language, "Space is low (below 5% free or below 1 GiB).",
                      "Слободниот простор е мал (под 5% или под 1 GiB).")
    return _label(language, "This measurement shows no shortage of disk space.",
                  "Мерењето покажува дека има доволно слободен простор.")


def _disk(language):
    volumes = _volumes()
    return "\n".join(_disk_evidence([v], language) + " " + _disk_status(v, language) for v in volumes)


_DISK_WORDS = set("disk disks drive storage space filesystem диск дискот дискови дисковите простор просторот".split())
_CAPACITY_WORDS = set(("full filling low left remaining free available used capacity usage much "
                       "полн полна полни преполн исполнет слободен слободни достапен "
                       "достапни зафатен искористен преостанат колку").split())
_QUESTION_WORDS = _DISK_WORDS | _CAPACITY_WORDS | set((
    "a an the my on of in is are am i it do have has there how why what show check tell me and "
    "nearly almost running out current please answer briefly short currently "
    "зошто дали имам има ми е се на за од во и мојот мојата речиси скоро уште останува "
    "моментално моменталниот провери прикажи кажи одговори накратко"
).split())


def _disk_question(question):
    # Answer only capacity questions. Other topics or requests for action go to the model.
    words = set(re.findall(r"[^\W_]+", question.casefold()))
    return bool(words & _DISK_WORDS and words & _CAPACITY_WORDS and words <= _QUESTION_WORDS)


def support_answer(question, language="en"):
    """Return local evidence plus an optional direct answer from the same measurements."""
    if not _disk_question(question):
        return diagnostics(question, language), None
    reply_language = "mk" if re.search(r"[а-шѓќљњѕџј]", question.casefold()) else "en"
    try:
        volumes = _volumes()
    except (OSError, ValueError):
        return (_label(language, "Disk — reading unavailable", "Диск — нема достапно мерење"),
                _label(reply_language, "I could not measure the free space on this filesystem.",
                       "Не можев да го измерам слободниот простор на овој датотечен систем."))
    lines = []
    for volume in volumes:
        fraction = volume.free / volume.total
        status = _disk_status(volume, reply_language)
        available = _label(reply_language, "free", "слободни")
        lines.append(f"{volume.path} — {volume.free / 2**30:.2f} GiB {available} ({fraction:.1%}). {status}")
    if any(_low_space(volume) for volume in volumes):
        lines.append(_label(reply_language, "To find which folders occupy the space, check their sizes in Dolphin.",
                            "За да видите кои папки го зафаќаат просторот, проверете ги нивните големини во Dolphin."))
    return _disk_evidence(volumes, language), "\n".join(lines)


def _ram(language):
    if sys.platform == "win32":
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_uint32), ("load", ctypes.c_uint32),
                        ("total", ctypes.c_uint64), ("available", ctypes.c_uint64),
                        ("other", ctypes.c_uint64 * 5)]

        data = MemoryStatus()
        data.length = ctypes.sizeof(data)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(data)):
            raise OSError("GlobalMemoryStatusEx")
        total, available = data.total, data.available
    else:
        fields = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            name, value = line.split(":", 1)
            if name in ("MemTotal", "MemAvailable"):
                fields[name] = int(value.split()[0]) * 1024
        total, available = fields["MemTotal"], fields["MemAvailable"]
    return (f"RAM — {(total - available) / 2**30:.1f} / {total / 2**30:.1f} GiB, "
            f"{available / 2**30:.1f} GiB " + _label(language, "available", "достапни"))


def _gpu(language):
    nvidia = (Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "nvidia-smi.exe"
              if os.name == "nt" else Path("/usr/bin/nvidia-smi"))
    if nvidia.is_file():
        return "GPU / VRAM (MiB) —\n" + "\n".join(_clean(row, 256) for row in
            _command([str(nvidia), "--query-gpu=name,memory.used,memory.total",
                      "--format=csv"]).splitlines()[:9])
    cards = []
    for card in sorted(Path("/sys/class/drm").glob("card[0-9]*")):
        if not card.name[4:].isdigit() or len(cards) >= 8:
            continue
        device = card / "device"
        vendor = (device / "vendor").read_text().strip()
        pci = (device / "device").read_text().strip()
        driver = (device / "driver").resolve().name
        cards.append(f"{card.name}  PCI {vendor}:{pci}  {driver}")
    if not cards:
        raise OSError("GPU")
    return "GPU — " + ", ".join(cards)


def _logs(question, language):
    use_user = "plasma" in question or "плазма" in question
    scope = (["--user", "-u", "plasma-plasmashell.service"] if use_user
             else ["-u", "ollama.service"])
    # journalctl JSON caps individual fields at 4096 bytes unless --all is set.
    result = _command(["/usr/bin/journalctl", *scope, "-b", "-p", "warning", "-n", "20",
                       "--no-pager", "-o", "json", "--output-fields=MESSAGE"])
    rows = [scope[-1] + " — " + _label(language, "recent warnings", "последни предупредувања")]
    for line in result.splitlines()[:20]:
        record = json.loads(line)
        if isinstance(record.get("MESSAGE"), str):
            rows.append(_clean(record["MESSAGE"], 300))
    if len(rows) == 1:
        rows.append(_label(language, "No readable matching entries.", "Нема достапни соодветни записи."))
    return "\n".join(rows)


def diagnostics(question: str, language="en") -> str:
    """Collect only relevant observations. Log contents cannot select operations."""
    query = question.casefold()
    checks = [
        ("Disk", _disk, ("disk", "space", "storage", "диск", "простор", "полн")),
        ("RAM", _ram, ("ram", "memory", "мемори", "рам")),
        ("GPU", _gpu, ("gpu", "graphics", "video", "nvidia", "графи", "видео")),
        ("Journal", lambda lang: _logs(query, lang), ("log", "journal", "лог", "запис", "дневник")),
    ]
    selected = [row for row in checks if any(word in query for word in row[2])]
    output = []
    for name, probe, _ in selected or checks[:3]:
        try:
            output.append(probe(language))
        except (OSError, subprocess.SubprocessError, ValueError, KeyError):
            output.append(name + " — " + _label(language, "reading unavailable", "нема достапно мерење"))
    return "\n".join(output)


@dataclass(frozen=True)
class Repair:
    target: object
    description: str


def _doctor():
    # Both the packaged application and source tree have this fixed sibling.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "adaptive"))
    try:
        import doctor
    except ImportError as exc:
        raise ValueError("KERNOVA System Help (kernova-performance) is unavailable.") from exc
    finally:
        sys.path.pop(0)
    return doctor


def prepare_repair(language="en") -> Repair:
    doctor = _doctor()
    try:
        target, muted = doctor.audio_state()
    except doctor.Unavailable as exc:
        raise ValueError(str(exc)) from exc
    if not muted:
        raise ValueError(_label(language, "The default output already has sound enabled.",
                                "Звукот на стандардниот излез е веќе вклучен."))
    return Repair(target, _label(language, f"Unmute playback output #{target.node} at its current volume?",
                                 f"Вклучи го звукот на излезот #{target.node} со сегашната јачина?"))


def apply_repair(repair: Repair):
    doctor = _doctor()
    try:
        if doctor.audio_state() != (repair.target, True):
            raise ValueError("The selected audio output or mute state changed.")
        doctor.command("wpctl", "set-mute", str(repair.target.node), "0")
        if doctor.audio_state() != (repair.target, False):
            raise ValueError("Could not verify the changed audio output.")
    except doctor.Unavailable as exc:
        raise ValueError(str(exc)) from exc


MAX_FILE_BYTES = 32 * 1024
_SKIP = {"node_modules", "vendor", "target", "build", "dist", "__pycache__", "venv"}
_SUFFIXES = set((".c .cc .cpp .h .hpp .cs .css .csv .go .html .ini .java .js .json .jsx .kt "
                 ".lua .md .mjs .php .py .qml .rb .rs .sh .sql .swift .toml .ts .tsx .txt "
                 ".vue .xml .yaml .yml").split())
_FILENAME = {"Dockerfile", "Makefile", "CMakeLists.txt", "README", "LICENSE"}
_BINARY = getattr(os, "O_BINARY", 0)
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


class StaleFile(ValueError):
    """The path, file or contents changed since the snapshot was read."""


@contextmanager
def _reviewed_file():
    # Formerly readable paths may disappear or become directories/links.
    try:
        yield
    except (FileNotFoundError, NotADirectoryError, IsADirectoryError, ValueError) as exc:
        raise StaleFile("The file changed. Review a fresh proposal.") from exc


def _parts(name):
    if not isinstance(name, str) or len(name) > 2048 or any(c in name for c in "\\:"):
        raise ValueError("Invalid project path.")
    parts = name.split("/")
    if (len(parts) > 16 or any(not p or p.startswith(".") or p in _SKIP or
            not all(c.isprintable() for c in p) for p in parts)):
        raise ValueError("Invalid project path.")
    return parts


def _id(st):
    return st.st_dev, st.st_ino


def _stamp(st):
    # The Windows CRT and path-stat APIs disagree on the meaning of ctime.
    ctime = st.st_ctime_ns if os.name == "posix" else None
    return _id(st), st.st_size, st.st_mtime_ns, ctime, st.st_mode


def _link(st):
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & 0x400)


def _validate_text(text):
    if (not isinstance(text, str) or len(text.encode("utf-8")) > MAX_FILE_BYTES or
            any(c not in "\t\n\r" and unicodedata.category(c) in ("Cc", "Cf") for c in text)):
        raise ValueError("Select a UTF-8 text file of at most 32 KiB without control characters.")


@dataclass(frozen=True)
class Snapshot:
    project: tuple
    path: str
    stamp: tuple
    text: str


@dataclass(frozen=True)
class Edit:
    before: Snapshot
    replacement: str
    diff: str


@dataclass(frozen=True)
class Directory:
    path: Path
    fd: int | None

    def at(self, name):
        return name if self.fd is not None else self.path / name

    def stat(self, name):
        return os.stat(self.at(name), dir_fd=self.fd, follow_symlinks=False)

    @contextmanager
    def child(self, name):
        path = self.path / name
        if self.fd is None:
            info = path.lstat()
            if _link(info) or not stat.S_ISDIR(info.st_mode):
                raise StaleFile("The project directory changed or contains a link.")
            yield Directory(path, None)
        else:
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | _NOFOLLOW, dir_fd=self.fd)
            try:
                yield Directory(path, fd)
            finally:
                os.close(fd)


class Project:
    """Read one selected folder. Apply a reviewed change to its original file."""

    def __init__(self, folder):
        self.root = Path(folder).absolute()
        if self.root.resolve(strict=True) != self.root or not self.root.is_dir():
            raise ValueError("Choose a real project directory.")
        self.key = _id(self.root.stat())

    @contextmanager
    def _directory(self, parts):
        with ExitStack() as stack:
            anchor = Path(self.root.anchor)
            if os.name == "nt":
                current = Directory(anchor, None)
            else:
                fd = os.open(anchor, os.O_RDONLY | os.O_DIRECTORY)
                stack.callback(os.close, fd)
                current = Directory(anchor, fd)
            for name in self.root.parts[1:]:
                current = stack.enter_context(current.child(name))
            if _id(os.fstat(current.fd) if current.fd is not None else current.path.stat()) != self.key:
                raise StaleFile("The selected project was moved or replaced.")
            for name in parts:
                current = stack.enter_context(current.child(name))
            yield current

    def list_files(self):
        found = []
        visited = 0

        def walk(directory, prefix):
            nonlocal visited
            with os.scandir(directory.fd if directory.fd is not None else directory.path) as entries:
                for entry in entries:
                    visited += 1
                    if visited > 8000 or len(found) >= 400:
                        break
                    relative = "/".join((*prefix, entry.name))
                    try:
                        _parts(relative)
                        info = entry.stat(follow_symlinks=False)
                        if _link(info):
                            continue
                        if stat.S_ISDIR(info.st_mode) and len(prefix) < 8:
                            with directory.child(entry.name) as child:
                                walk(child, (*prefix, entry.name))
                        elif (stat.S_ISREG(info.st_mode) and info.st_size <= MAX_FILE_BYTES
                              and (entry.name in _FILENAME or Path(entry.name).suffix.lower() in _SUFFIXES)):
                            found.append(relative)
                    except (OSError, ValueError):
                        continue
        with self._directory(()) as directory:
            walk(directory, ())
        return sorted(found)

    def _read_at(self, parent, name, path):
        info = parent.stat(name)
        if _link(info) or not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
            raise ValueError("Select a small regular text file inside the project.")
        flags = os.O_RDONLY | _NOFOLLOW | getattr(os, "O_NONBLOCK", 0) | _BINARY
        with os.fdopen(os.open(parent.at(name), flags, dir_fd=parent.fd), "rb") as source:
            if _stamp(os.fstat(source.fileno())) != _stamp(info):
                raise StaleFile("File changed before reading.")
            data = source.read(MAX_FILE_BYTES + 1)
            if len(data) > MAX_FILE_BYTES or _stamp(os.fstat(source.fileno())) != _stamp(info):
                raise StaleFile("File changed while reading.")
        text = data.decode("utf-8")
        _validate_text(text)
        return Snapshot(self.key, path, _stamp(info), text)

    def read(self, path):
        *parts, name = _parts(path)
        with self._directory(parts) as directory:
            return self._read_at(directory, name, path)

    def propose(self, snapshot, replacement_text):
        if snapshot.project != self.key:
            raise StaleFile("Different project selected.")
        _validate_text(replacement_text)
        if "\r\n" in snapshot.text and "\n" not in snapshot.text.replace("\r\n", ""):
            replacement_text = replacement_text.replace("\r\n", "\n").replace("\n", "\r\n")
            _validate_text(replacement_text)
        lines = unified_diff(snapshot.text.splitlines(True), replacement_text.splitlines(True),
                             fromfile="a/" + snapshot.path, tofile="b/" + snapshot.path)
        diff = "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
                       for line in lines)
        return Edit(snapshot, replacement_text, diff)

    def apply(self, edit):
        before = edit.before
        *parts, name = _parts(before.path)
        if before.project != self.key:
            raise StaleFile("Different project selected.")
        _validate_text(edit.replacement)
        with _reviewed_file(), self._directory(parts) as parent:
            if parent.fd is not None:
                import fcntl
                fcntl.flock(parent.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if self._read_at(parent, name, before.path) != before:
                raise StaleFile("File changed. Review a fresh proposal.")
            if not edit.diff:
                return
            temp = ".kernova-ai-" + secrets.token_hex(16)
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | _NOFOLLOW | _BINARY
            fd = os.open(parent.at(temp), flags, 0o600, dir_fd=parent.fd)
            try:
                with os.fdopen(fd, "wb") as output:
                    output.write(edit.replacement.encode("utf-8"))
                    output.flush()
                    if parent.fd is not None:
                        os.fchmod(output.fileno(), stat.S_IMODE(before.stamp[-1]) & 0o777)
                    os.fsync(output.fileno())
                # Re-open by project path to catch a moved ancestor during review/apply.
                with self._directory(parts) as current:
                    if self._read_at(current, name, before.path) != before:
                        raise StaleFile("File changed. Review a fresh proposal.")
                    if parent.fd is not None and _id(os.fstat(current.fd)) != _id(os.fstat(parent.fd)):
                        raise StaleFile("The parent directory was replaced.")
                    os.replace(parent.at(temp), current.at(name), src_dir_fd=parent.fd, dst_dir_fd=current.fd)
                if parent.fd is not None:
                    os.fsync(parent.fd)
            finally:
                with suppress(FileNotFoundError):
                    os.unlink(parent.at(temp), dir_fd=parent.fd)
