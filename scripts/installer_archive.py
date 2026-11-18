"""Authenticate the unmodified Debian Installer images used by trixie live-build."""

import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen


DIST = "https://deb.debian.org/debian/dists/trixie"
IMAGE_DIR = "main/installer-amd64/current/images"
FILES = ("cdrom/vmlinuz", "cdrom/initrd.gz", "cdrom/gtk/vmlinuz", "cdrom/gtk/initrd.gz")
KEYRING = "/usr/share/keyrings/debian-archive-keyring.gpg"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def release_hash(release):
    if not re.search(r"^Codename: trixie$", release, re.M) or not re.search(r"^Origin: Debian$", release, re.M):
        raise ValueError("Expected a Debian trixie Release")
    section = re.search(r"^SHA256:\n((?: [^\n]+\n)+)", release, re.M)
    if section:
        for line in section[1].splitlines():
            checksum, size, name = line.split()
            if name == f"{IMAGE_DIR}/SHA256SUMS" and re.fullmatch("[0-9a-f]{64}", checksum):
                return checksum, int(size)
    raise ValueError("The signed Release lacks the installer SHA256 manifest")


def verified_hashes(evidence):
    with tempfile.TemporaryDirectory() as temporary:
        release = Path(temporary) / "Release"
        # Read only gpgv's authenticated cleartext, never the outer signed envelope.
        subprocess.run(["gpgv", "--keyring", KEYRING, "--output", release, evidence / "InRelease"], check=True)
        expected, length = release_hash(release.read_text(encoding="utf-8"))
    sums = evidence / "SHA256SUMS"
    if sums.stat().st_size != length or digest(sums) != expected:
        raise ValueError("Installer SHA256SUMS does not match the signed Debian Release")
    entries = {}
    for line in sums.read_text().splitlines():
        checksum, name = line.split(maxsplit=1)
        name = name.removeprefix("./")
        if name in FILES:
            if name in entries or not re.fullmatch("[0-9a-f]{64}", checksum):
                raise ValueError(f"Invalid checksum entry for {name}")
            entries[name] = checksum
    if entries.keys() != set(FILES):
        raise ValueError("The Debian installer manifest is missing a required file")
    return entries


def download(url, path):
    with urlopen(url, timeout=60) as response, path.open("xb") as stream:
        shutil.copyfileobj(response, stream)


def prepare(work, evidence):
    evidence.mkdir()
    download(f"{DIST}/InRelease", evidence / "InRelease")
    base = f"{DIST}/{IMAGE_DIR}"
    download(f"{base}/SHA256SUMS", evidence / "SHA256SUMS")
    hashes = verified_hashes(evidence)
    cache = work / "cache/installer_debian-installer"
    cache.mkdir(parents=True)
    for name, checksum in hashes.items():
        url = f"{base}/{name}"
        # Debian live-build caches these exact URLs with slashes mapped to '_'.
        # validate-iso independently checks the bytes actually placed on the ISO.
        target = cache / url.replace("/", "_")
        download(url, target)
        if digest(target) != checksum:
            raise ValueError(f"Installer download failed authentication: {name}")
    print("Authenticated Debian Installer kernels and initrds (text and graphical).")


if __name__ == "__main__":
    work, evidence = map(Path, sys.argv[1:])
    if not (work / ".kernova-work").is_file():
        sys.exit("Expected a fresh live-build work directory.")
    prepare(work, evidence)
