"""Read the running system without starting privileged operations."""

from dataclasses import dataclass
from pathlib import Path
import json
import os
import platform
import re
import shlex
import subprocess


@dataclass(frozen=True)
class Action:
    arguments: tuple[str, ...]
    package: str
    extra_package: tuple[str, Path] | None = None

    def missing_package(self) -> str | None:
        executable = Path(self.arguments[0])
        if not executable.is_file() or not os.access(executable, os.X_OK):
            return self.package
        if self.extra_package is not None:
            package, marker = self.extra_package
            if not marker.is_file():
                return package
        return None


SETTINGS_MODULES = {
    "network": ("kcm_networkmanagement", "plasma-nm"),
    "bluetooth_settings": ("kcm_bluetooth", "bluedevil"),
    "display_settings": ("kcm_kscreen", "kscreen"),
    "sound_settings": ("kcm_pulseaudio", "plasma-pa"),
    "power_settings": ("kcm_powerdevilprofilesconfig", "powerdevil"),
    "appearance_settings": ("kcm_lookandfeel", "plasma-workspace"),
    "wallpaper_settings": ("kcm_wallpaper", "plasma-workspace"),
    "default_app_settings": ("kcm_componentchooser", "plasma-desktop"),
    "flatpak_settings": ("kcm_flatpak", "kde-config-flatpak"),
    "notification_settings": ("kcm_notifications", "plasma-workspace"),
    "desktop_search_settings": ("kcm_plasmasearch", "plasma-desktop"),
    "file_search_settings": ("kcm_baloofile", "plasma-desktop"),
    "web_search_settings": ("kcm_webshortcuts", "kio-extras"),
    "account_settings": ("kcm_kaccounts", "kaccounts-integration"),
    "keyboard_settings": ("kcm_keyboard", "plasma-desktop"),
    "shortcut_settings": ("kcm_keys", "plasma-desktop"),
    "mouse_settings": ("kcm_mouse", "plasma-desktop"),
    "touchpad_settings": ("kcm_touchpad", "plasma-desktop"),
    "workspace_settings": ("kcm_workspace", "plasma-desktop"),
    "language_settings": ("kcm_regionandlang", "plasma-workspace"),
    "date_settings": ("kcm_clock", "plasma-desktop"),
    "accessibility_settings": ("kcm_access", "plasma-desktop"),
    "user_settings": ("kcm_users", "plasma-workspace"),
}


ACTIONS = {
    "settings": Action(("/usr/bin/systemsettings",), "systemsettings"),
    **{
        key: Action(("/usr/bin/systemsettings", module), "systemsettings",
                    (package, Path(f"/usr/share/applications/{module}.desktop")))
        for key, (module, package) in SETTINGS_MODULES.items()
    },
    "software": Action(("/usr/bin/kernova-get-apps",), "kernova-desktop"),
    "chrome": Action(("/usr/bin/kernova-get-apps", "chrome"), "kernova-desktop"),
    "viber": Action(("/usr/bin/kernova-get-apps", "viber"), "kernova-desktop"),
    "telegram": Action(("/usr/bin/kernova-get-apps", "telegram"), "kernova-desktop"),
    "whatsapp": Action(("/usr/bin/kernova-get-apps", "whatsapp"), "kernova-desktop"),
    "updates": Action(("/usr/bin/plasma-discover", "--mode", "update"), "plasma-discover"),
    "info": Action(("/usr/bin/kinfocenter",), "kinfocenter"),
    "browser": Action(("/usr/bin/firefox-esr",), "firefox-esr"),
    "files": Action(("/usr/bin/dolphin",), "dolphin"),
    "editor": Action(("/usr/bin/kate",), "kate"),
    "terminal": Action(("/usr/bin/konsole",), "konsole"),
}


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def string_mapping(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {key: value for key, value in data.items() if isinstance(value, str)}


def language_for(locale_name: str) -> str:
    return "mk" if re.split(r"[_@.\-]", locale_name.lower(), maxsplit=1)[0] == "mk" else "en"


def boot_session(command_line: str | None) -> str:
    if not command_line or not command_line.strip():
        return "unknown"
    try:
        options = shlex.split(command_line)
    except ValueError:
        return "unknown"
    return "live" if "boot=live" in options else "installed"


def os_pretty_name(os_release: str) -> str | None:
    values = {}
    for line in os_release.splitlines():
        key, separator, value = line.partition("=")
        if key not in {"PRETTY_NAME", "NAME"} or not separator:
            continue
        try:
            parts = shlex.split(value)
        except ValueError:
            continue
        if len(parts) == 1 and parts[0]:
            values[key] = parts[0]
    return values.get("PRETTY_NAME") or values.get("NAME")


def cpu_name(cpuinfo: str) -> str | None:
    for line in cpuinfo.splitlines():
        key, _, value = line.partition(":")
        if key.strip() == "model name" and value.strip():
            return value.strip()
    return None


def memory_kib(meminfo: str) -> int | None:
    match = re.search(r"(?m)^MemTotal:[ \t]+([0-9]{1,20})[ \t]+kB[ \t]*$", meminfo)
    return int(match[1]) if match and int(match[1]) > 0 else None


def pci_gpu_names(pci_devices: Path = Path("/sys/bus/pci/devices")) -> str | None:
    device_addresses = {}
    for device in sorted(pci_devices.glob("*")):
        device_class = (read_text(device / "class") or "").strip()
        if not re.fullmatch(r"0x03[0-9a-fA-F]{4}", device_class):
            continue
        vendor = (read_text(device / "vendor") or "").strip()
        model = (read_text(device / "device") or "").strip()
        if re.fullmatch(r"0x[0-9a-fA-F]{4}", vendor) and re.fullmatch(r"0x[0-9a-fA-F]{4}", model):
            device_addresses[device.name] = f"PCI {vendor[2:]}:{model[2:]}"
        else:
            device_addresses[device.name] = device.name
    if not device_addresses:
        return None

    # The PCI class identifies all display controllers, including secondary GPUs.
    try:
        result = subprocess.run(
            ("/usr/bin/lspci", "-D", "-mm"),
            capture_output=True, check=True, text=True, encoding="utf-8",
            errors="replace", timeout=2,
            env={**os.environ, "LC_ALL": "C"},
        )
    except (OSError, subprocess.SubprocessError):
        return "\n".join(device_addresses.values())

    for line in result.stdout.splitlines():
        try:
            fields = shlex.split(line)
        except ValueError:
            continue
        if len(fields) >= 4 and fields[0] in device_addresses:
            device_addresses[fields[0]] = f"{fields[2]} {fields[3]}"
    return "\n".join(device_addresses.values())


def collect_system_info() -> dict[str, str | int | None]:
    os_release = read_text(Path("/etc/os-release"))
    if os_release is None:
        os_release = read_text(Path("/usr/lib/os-release"))
    return {
        "base": os_pretty_name(os_release or ""),
        "session": boot_session(read_text(Path("/proc/cmdline"))),
        "kernel": platform.release() or None,
        "architecture": platform.machine() or None,
        "cpu": cpu_name(read_text(Path("/proc/cpuinfo")) or ""),
        "memory": memory_kib(read_text(Path("/proc/meminfo")) or ""),
        "graphics": pci_gpu_names(),
    }
