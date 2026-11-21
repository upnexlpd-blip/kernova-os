"""Exercise the installed CLI in an isolated QEMU desktop user's PipeWire session."""
import json
from pathlib import Path
import subprocess


def run(*args, **kwargs):
    return subprocess.run(args, capture_output=True, text=True, timeout=45, **kwargs)


def report(*args):
    proc = run("kernova-doctor", *args, "--json")
    assert proc.returncode in (0, 1, 2), proc.returncode
    return {r["id"]: r for r in json.loads(proc.stdout)["checks"]}


def main():
    if Path("/sys/class/dmi/id/sys_vendor").read_text().strip() != "QEMU":
        raise SystemExit("Run inside the disposable KERNOVA QEMU desktop.")
    target = "@DEFAULT_AUDIO_SINK@"
    before = run("wpctl", "get-volume", target, check=True).stdout.strip()
    volume = before.removesuffix(" [MUTED]")
    identity = run("wpctl", "inspect", target, check=True).stdout
    node = identity.split(",", 1)[0].removeprefix("id ")
    assert node.isdecimal()
    try:
        run("wpctl", "set-mute", node, "1", check=True)
        first = report("scan")
        assert "network.online" not in first
        assert first["audio.mute"]["fix_id"] == "audio.unmute"
        assert first["audio.mute"]["status"] == "PROBLEM"
        for row in first.values():
            print(row["id"], row["status"], row["evidence"])
        muted = volume + " [MUTED]"
        assert run("wpctl", "get-volume", node, check=True).stdout.strip() == muted
        assert run("kernova-doctor", "fix", "audio.unmute", input="no\n").returncode == 1
        assert run("wpctl", "get-volume", node, check=True).stdout.strip() == muted
        print("Scan and cancelled repair preserved mute and volume.")
        result = run("kernova-doctor", "fix", "audio.unmute", input="yes\n", check=True)
        print(result.stdout.strip())
        assert "Verified mute off" in result.stdout
        assert run("wpctl", "get-volume", node, check=True).stdout.strip() == volume
        assert report("check", "audio")["audio.mute"]["status"] == "OK"
        online = report("check", "network", "--online")
        print("Optional probe:", online["network.online"]["status"], online["network.online"]["evidence"])
        assert online["network.local"]["status"] == first["network.local"]["status"]
        assert run("wpctl", "inspect", target, check=True).stdout == identity
        print("Read-back volume before and after unmute:", volume)
    finally:
        if run("wpctl", "inspect", target).stdout == identity:
            run("wpctl", "set-mute", node, "1" if before.endswith("[MUTED]") else "0", check=True)


if __name__ == "__main__":
    main()
