#!/usr/bin/python3
"""Launch an ordinary user's workload with a process-local Linux scheduling policy."""
import argparse
import ctypes
from dataclasses import dataclass
import os
import re
import shutil
import subprocess
import sys


@dataclass(frozen=True)
class Profile:
    label: str
    description: str
    slack_ns: int
    nice: int
    batch: bool
    power: str | None


PROFILES = {
    "gaming": Profile("Gaming Mode", "Short timer delays for interactive games.", 10_000, 0, False, "performance"),
    "coding": Profile("Coding Mode", "Batch scheduling and modest priority for builds while you edit.", 100_000, 3, True, None),
    "battery": Profile("Battery Saver", "Group wakeups and lower background workload priority.", 10_000_000, 8, True, "power-saver"),
    "maximum": Profile("Maximum Performance", "Minimum timer slack for latency-sensitive workloads.", 1, 0, False, "performance"),
}


def power_modes():
    if not shutil.which("powerprofilesctl"):
        return set()
    try:
        result = subprocess.run(["powerprofilesctl", "list"], capture_output=True, text=True, timeout=3,
                                env={**os.environ, "LC_ALL": "C"}, check=True)
    except (OSError, subprocess.SubprocessError):
        return set()
    return set(re.findall(r"^\s*\*?\s*(performance|balanced|power-saver):\s*$", result.stdout, re.M))


def apply_process_policy(profile):
    # Linux PR_SET_TIMERSLACK applies to this thread and is inherited across exec.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(29, ctypes.c_ulong(profile.slack_ns), 0, 0, 0) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err))
    if profile.batch:
        os.sched_setscheduler(0, os.SCHED_BATCH, os.sched_param(0))
    if profile.nice:
        os.nice(profile.nice)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=PROFILES)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    argv = args.command
    if argv[:1] == ["--"]:
        argv = argv[1:]
    if not argv:
        parser.error("Provide a program to launch.")
    profile = PROFILES[args.profile]
    try:
        apply_process_policy(profile)
        if profile.power and profile.power in power_modes():
            argv = ["powerprofilesctl", "launch", "--profile", profile.power, "--reason",
                    "KERNOVA " + profile.label, "--", *argv]
        os.execvp(argv[0], argv)
    except OSError as exc:
        parser.exit(1, f"Could not launch {argv[0]}: {exc}\n")


if __name__ == "__main__":
    main()
