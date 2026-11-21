#!/usr/bin/python3 -B
"""On-demand local diagnostics for the KERNOVA desktop."""
import argparse
from dataclasses import asdict, dataclass
import json
import os
import platform
import re
import subprocess
import sys

from status import pressure, read_status


class Unavailable(Exception):
    """Only privacy-safe evidence belongs in this exception."""


@dataclass(frozen=True)
class Finding:
    id: str
    status: str
    evidence: str
    explanation: str
    next_step: str
    fix_id: str | None = None


def command(*args, timeout=5, strict=False):
    tool = args[0]
    env = dict(os.environ, LC_ALL="C", PIPEWIRE_REMOTE="pipewire-0")
    try:
        proc = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                              errors="replace", env=env, timeout=timeout)
    except FileNotFoundError:
        raise Unavailable(f"{tool} is missing.") from None
    except subprocess.TimeoutExpired:
        raise Unavailable(f"{tool} timed out after {timeout} seconds.") from None
    if "permission denied" in proc.stderr.lower() or "access denied" in proc.stderr.lower():
        raise Unavailable(f"{tool} reported a permission denial.")
    if proc.returncode or (strict and proc.stderr.strip()):
        raise Unavailable(f"{tool} exited {proc.returncode}" +
                          (" with a diagnostic." if proc.stderr.strip() else "."))
    return proc.stdout.strip()


def network():
    state = command("nmcli", "-t", "-f", "STATE", "general")
    if state in ("connected", "connected (local only)", "connected (site only)"):
        return "OK", f"NetworkManager state = {state}", "A local connection is active."
    if state in ("disconnected", "asleep"):
        return "PROBLEM", f"NetworkManager state = {state}", "No active network connection."
    if state in ("connecting", "disconnecting", "unknown"):
        raise Unavailable(f"NetworkManager state = {state}")
    raise Unavailable("Unrecognized NetworkManager state.")


def internet():
    code = command("curl", "-q", "--noproxy", "*", "--head", "--silent", "--output", "/dev/null",
                   "--write-out", "%{http_code}", "--connect-timeout", "2", "--max-time", "4",
                   "https://deb.debian.org/debian/dists/trixie/InRelease")
    if code == "200":
        return "OK", "deb.debian.org returned HTTPS 200.", "The Debian endpoint was reachable."
    raise Unavailable("Debian endpoint returned " + (f"HTTP {code}." if re.fullmatch(r"\d{3}", code)
                                                     else "an unrecognized response."))


@dataclass(frozen=True)
class Sink:
    node: int
    serial: int
    service_instance: str


def selected_sink():
    # Avoid activating a stopped PipeWire server by connecting to its socket.
    unit = command("systemctl", "--user", "show", "pipewire.service", "-p", "ActiveState", "-p", "InvocationID")
    instance = re.search(r"^InvocationID=([a-f0-9]{32})$", unit, re.M)
    if "ActiveState=active" not in unit.splitlines() or not instance:
        raise Unavailable("No active PipeWire service in this user session.")
    info = command("wpctl", "inspect", "@DEFAULT_AUDIO_SINK@")
    node = re.search(r"^id (\d+), type PipeWire:Interface:Node\b", info, re.M)
    serial = re.search(r'^\s*\*?\s*object\.serial = "(\d+)"\s*$', info, re.M)
    if not node or not serial or not re.search(r'^\s*\*?\s*media\.class = "Audio/Sink"\s*$', info, re.M):
        raise Unavailable("WirePlumber did not identify a default Audio/Sink.")
    return Sink(int(node[1]), int(serial[1]), instance[1])


def audio_state():
    sink = selected_sink()
    volume = command("wpctl", "get-volume", str(sink.node))
    match = re.fullmatch(r"Volume: \d+(?:\.\d+)?( \[MUTED\])?", volume)
    if not match:
        raise Unavailable("WirePlumber returned an unrecognized mute state.")
    if selected_sink() != sink:
        raise Unavailable("The selected output changed while reading its mute state.")
    return sink, bool(match[1])


UNMUTE = "audio.unmute"


def audio():
    sink, muted = audio_state()
    evidence = f"Default output #{sink.node}, mute={'on' if muted else 'off'}."
    if muted:
        return "PROBLEM", evidence, "The selected playback output is muted."
    return "OK", evidence, "The selected playback output is unmuted in software."


def disk_capacity(inodes=False):
    fs = os.statvfs("/")
    total = fs.f_files if inodes else fs.f_blocks
    available = fs.f_favail if inodes else fs.f_bavail
    if total == 0 and inodes:
        return "NOT_APPLICABLE", "/ reports zero total inodes.", "No fixed inode count is available."
    if not 0 <= available <= total or total <= 0 or fs.f_frsize <= 0:
        raise Unavailable("statvfs returned inconsistent filesystem counters.")
    free = f"{available} of {total} inodes" if inodes else f"{available * fs.f_frsize} bytes"
    evidence = f"/ has {free} available ({100 * available / total:.1f}%)."
    if available * 100 < total * 5:
        return "PROBLEM", evidence, "Available capacity is below the 5% warning threshold."
    return "OK", evidence, "Available capacity meets the 5% threshold."


def packages():
    status = command("dpkg-query", "-W", "-f=${db:Status-Status}", "kernova-performance", strict=True)
    if status in ("unpacked", "half-configured", "half-installed", "triggers-awaited", "triggers-pending"):
        return "PROBLEM", f"kernova-performance state = {status}", "Package configuration is incomplete."
    if status != "installed":
        raise Unavailable("dpkg-query could not confirm an installed performance package.")
    if command("dpkg", "--audit", strict=True, timeout=15):
        return "PROBLEM", "dpkg --audit returned findings.", "The package database needs attention."
    return "OK", "kernova-performance installed; dpkg --audit empty.", "dpkg found no pending issues."


def updates():
    flags = ("-o", "Dir::Cache::pkgcache=", "-o", "Dir::Cache::srcpkgcache=")
    policy = command("apt-cache", *flags, "policy", "kernova-performance", strict=True, timeout=10)
    version = r"([0-9][a-zA-Z0-9.+:~\-]*)"
    installed = re.search(r"^  Installed: " + version + "$", policy, re.M)
    candidate = re.search(r"^  Candidate: " + version + "$", policy, re.M)
    if not installed or not candidate:
        raise Unavailable("APT has no usable installed or candidate version.")
    # An installed version can still be a candidate when indexes are absent.
    indexed = command("apt-cache", *flags, "madison", "kernova-performance", strict=True, timeout=10)
    if not re.search(r"^\s*kernova-performance\s*\|\s*" + version + r"\s*\|\s*\S", indexed, re.M):
        raise Unavailable(f"Installed {installed[1]}. No indexed KERNOVA package is available.")
    evidence = f"kernova-performance installed {installed[1]}, cached candidate {candidate[1]}."
    return "OK", evidence, ("APT selects the installed version from local metadata."
                            if installed[1] == candidate[1] else "APT selects a different package version.")


def adaptive():
    unit = command("systemctl", "show", "kernova-adaptive.service", "-p", "ActiveState", "--value")
    if unit in ("inactive", "failed"):
        return "PROBLEM", f"ActiveState={unit}", "The Adaptive Engine service is stopped."
    if unit != "active":
        raise Unavailable("systemd did not confirm an active Adaptive Engine.")
    data = read_status()
    state = data.get("state")
    enabled, override = data.get("enabled"), data.get("external_override")
    if type(enabled) is not bool or type(override) is not bool:
        raise Unavailable("Adaptive status lacks valid policy flags.")
    evidence = f"State={state}, automation={'on' if enabled else 'off'}, manual override={'on' if override else 'off'}."
    if state == "UNAVAILABLE":
        reasons = data.get("unavailable_reasons")
        if reasons == ["battery: no present system battery"]:
            return "NOT_APPLICABLE", evidence, "UPower has no present system battery."
        if isinstance(reasons, list) and any(isinstance(r, str) and r.startswith("configuration:") for r in reasons):
            return "PROBLEM", "The engine rejected its configuration.", "The adaptive thresholds could not be loaded."
        raise Unavailable("The engine reports UNAVAILABLE. Power or provider data could not be validated.")
    if state == "EXTERNAL_OVERRIDE" and enabled and override:
        return "OK", evidence, "Automation is yielding to a manual profile choice."
    if state == "AUTO" and enabled and not override:
        return "OK", evidence, "Automatic policy is active."
    if state == "OBSERVE" and not enabled and not override:
        return "OK", evidence, "The engine is observing with automation disabled."
    raise Unavailable("Adaptive status contains an unrecognized policy state.")


def kernel_pressure():
    values = pressure()
    found = [key for key in ("cpu", "memory", "io")
             if isinstance((values[key] or {}).get("some", {}).get("total"), int)]
    evidence = "PSI counters present: " + (", ".join(found) or "none") + "."
    if len(found) != 3:
        raise Unavailable(evidence)
    return "OK", evidence, "CPU, memory and I/O pressure counters are readable."


CHECKS = {
    "network.local": (network, "Check the Network and Wi-Fi settings in Plasma."),
    "network.online": (internet, "Retry the optional HTTPS check when internet access is expected."),
    "audio.mute": (audio, "Check the default output in Plasma Sound or run wpctl status."),
    "updates.dpkg": (packages, "Review dpkg --audit and the transaction history in Discover."),
    "updates.candidate": (updates, "Open Discover to review updates and refresh package lists when online."),
    "disk.space": (disk_capacity, "Review filesystem usage with df -h /."),
    "disk.inodes": (lambda: disk_capacity(True), "Review inode usage with df -i /."),
    "adaptive.policy": (adaptive, "Inspect kernova-adaptive status and systemctl status kernova-adaptive."),
    "adaptive.pressure": (kernel_pressure, "Inspect kernova-adaptive report --json for kernel pressure readings."),
}


def platform_issue():
    if sys.platform == "linux":
        try:
            release = platform.freedesktop_os_release()
        except OSError:
            return "UNKNOWN", "Cannot read os-release."
        if not release.get("ID") or not release.get("VERSION_ID"):
            return "UNKNOWN", "Missing OS identification."
        if release["ID"] == "debian" and release["VERSION_ID"] == "13":
            return None
    return "NOT_APPLICABLE", "System Help v1 targets the Debian 13 KERNOVA stack."


def check(key, issue=None):
    probe, step = CHECKS[key]
    fix = None
    try:
        if issue:
            status, evidence = issue
            explanation = "Platform requirements could not be confirmed."
        else:
            status, evidence, explanation = probe()
            if key == "audio.mute" and status == "PROBLEM":
                fix = UNMUTE
    except (Unavailable, OSError, ValueError) as exc:
        status, explanation = "UNKNOWN", "Insufficient data to complete this check."
        evidence = str(exc) if isinstance(exc, Unavailable) else type(exc).__name__
    return Finding(key, status, evidence, explanation, step, fix)


def repair():
    issue = platform_issue()
    if issue:
        print(issue[1])
        return 1
    try:
        target, muted = audio_state()
        if not muted:
            print(f"Default output #{target.node} already has mute off.")
            return 1
        print(f"Unmute default playback output #{target.node}? Volume will stay at its current setting.")
        if input("Type yes to apply: ").strip().lower() != "yes":
            print("Cancelled.")
            return 1
        if audio_state() != (target, True):
            print("Output or mute state changed. Repair cancelled.")
            return 1
        try:
            command("wpctl", "set-mute", str(target.node), "0")
        except (Unavailable, OSError) as exc:
            # A timeout can arrive after the server applied the request.
            detail = str(exc) if isinstance(exc, Unavailable) else type(exc).__name__
            print(f"Unmute command reported an error. {detail} Checking the output.")
        current, muted = audio_state()
        if current != target:
            print("Selected output changed. The original output could not be verified.")
        elif not muted:
            print(f"Verified mute off on output #{target.node}. Play a local sound to confirm playback.")
            return 0
        else:
            print(f"Verified that output #{target.node} is still muted.")
    except (EOFError, KeyboardInterrupt):
        print("Confirmation or verification interrupted.")
    except (Unavailable, OSError) as exc:
        detail = str(exc) if isinstance(exc, Unavailable) else type(exc).__name__
        print(f"Repair unverified. {detail}")
    return 1


def main(argv=None):
    cli = argparse.ArgumentParser(prog="kernova-doctor", description=__doc__)
    sub = cli.add_subparsers(dest="action", required=True)
    scan = sub.add_parser("scan")
    one = sub.add_parser("check")
    one.add_argument("area", choices=["network", "audio", "updates", "disk", "adaptive"])
    for parser in (scan, one):
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--online", action="store_true", help="also probe Debian over HTTPS (4s)")
    sub.add_parser("fix").add_argument("repair", choices=[UNMUTE])
    args = cli.parse_args(argv)
    if args.action == "fix":
        return repair()
    area = getattr(args, "area", None)
    if args.online and area not in (None, "network"):
        cli.error("--online applies to scan or check network")
    issue = platform_issue()
    rows = [check(key, issue) for key in CHECKS if (area is None or key.split(".")[0] == area)
            and (key != "network.online" or args.online)]
    if args.json:
        print(json.dumps({"schema_version": 1, "checks": [asdict(row) for row in rows]}, indent=2))
    else:
        for row in rows:
            print(f"{row.status}  {row.id}  {row.evidence}\n  {row.explanation}\n  {row.next_step}")
            if row.fix_id:
                print(f"  Available repair: kernova-doctor fix {row.fix_id}")
    if any(row.status == "PROBLEM" for row in rows):
        return 1
    if any(row.status == "UNKNOWN" for row in rows) or all(row.status == "NOT_APPLICABLE" for row in rows):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
