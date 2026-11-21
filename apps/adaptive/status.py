#!/usr/bin/python3
"""Local status, administrative control and Linux pressure snapshots."""
import argparse
import json
from pathlib import Path
import os
import secrets
import socket

RUN = Path("/run/kernova-adaptive")
STATE = Path("/var/lib/kernova-adaptive/settings.json")
CONFIG = Path("/etc/kernova/adaptive.json")


def atomic(path, data):
    tmp = path.with_suffix(".new")
    with tmp.open("w") as stream:
        json.dump(data, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def pressure(root=Path("/proc/pressure")):
    result = {}
    for resource in ("cpu", "memory", "io"):
        try:
            rows = {}
            for line in (root / resource).read_text().splitlines():
                scope, *fields = line.split()
                rows[scope] = {k: int(v) if k == "total" else float(v)
                               for k, v in (field.split("=") for field in fields)}
            result[resource] = rows or None
        except (OSError, ValueError):
            result[resource] = None
    return result


def read_status():
    status = json.loads((RUN / "status.json").read_text())
    if not isinstance(status, dict):
        raise ValueError("invalid service status")
    return status


def main():
    parser = argparse.ArgumentParser(prog="kernova-adaptive")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ("status", "report"):
        sub.add_parser(cmd).add_argument("--json", action="store_true")
    sub.add_parser("auto").add_argument("choice", choices=("on", "off"))
    args = parser.parse_args()
    if args.cmd == "auto":
        if os.geteuid():
            parser.exit(1, "Run auto on/off with sudo.\n")
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
                client.settimeout(25)
                client.bind("\0kernova-" + secrets.token_hex(16))
                client.sendto(args.choice.encode(), str(RUN / "control"))
                response = client.recv(1024).decode()
                if response != "ok":
                    parser.exit(1, response + "\n")
        except OSError as exc:
            parser.exit(1, f"Service control unavailable: {exc}\n")
        return
    try:
        status = read_status()
    except (OSError, ValueError):
        status = {"state": "UNAVAILABLE", "reason": "service status unavailable"}
    if args.cmd == "report":
        status["pressure"] = pressure()
    print(json.dumps(status, indent=2) if args.json else
          "\n".join(f"{key}: {value}" for key, value in status.items()))


if __name__ == "__main__":
    main()
