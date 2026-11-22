#!/bin/sh
set -eu
test "${KERNOVA_LIFECYCLE_CHROOT:-}" = 1
test -r /tmp/expected-version
test -d /tmp/older && test -d /tmp/current
export DEBIAN_FRONTEND=noninteractive LC_ALL=C
version=$(cat /tmp/expected-version)
packages='kernova-branding kernova-default-settings kernova-welcome kernova-performance kernova-desktop kernova-window-tools'
core='kernova-desktop plasma-workspace plasma-desktop kwin-wayland sddm firefox-esr'
skel=/etc/skel/.config/kdeglobals
newhome=/home/kernova-new
originalhome=/home/kernova-existing

check_installed() {
    test "$(dpkg-query -W -f='${db:Status-Status}' "$1")" = installed
}

echo "Testing Debian package lifecycle, fixture ${version}~test1 -> $version"
sha256sum /usr/lib/os-release /etc/os-release > /tmp/os-release.sha256
dpkg-query -S /etc/os-release /usr/lib/os-release
useradd --create-home kernova-existing
install -d -o kernova-existing -g kernova-existing "$originalhome/.config"
printf '[KDE]\nLookAndFeelPackage=org.kde.breeze.desktop\n' > "$originalhome/.config/kdeglobals"
chown kernova-existing:kernova-existing "$originalhome/.config/kdeglobals"
apt-get update
apt-get -y --no-install-recommends install /tmp/older/*.deb
for name in $packages; do
    test "$(dpkg-query -W -f='${Version}' "$name")" = "${version}~test1"
done
useradd --create-home kernova-new
cmp "$skel" "$newhome/.config/kdeglobals"
test "$(stat -c %U "$newhome/.config/kdeglobals")" = kernova-new
grep -Fxq 'LookAndFeelPackage=org.kernova.night' "$newhome/.config/kdeglobals"
grep -Fxq 'LookAndFeelPackage=org.kde.breeze.desktop' "$originalhome/.config/kdeglobals"
sed -i 's/org.kernova.night/org.kde.breeze.desktop/' "$newhome/.config/kdeglobals"
printf '\n# Site-specific setting\n' >> "$skel"
sha256sum "$skel" "$newhome/.config/kdeglobals" "$originalhome/.config/kdeglobals" > /tmp/preserve.sha256
echo 'Upgrading a modified conffile and two existing user profiles'
apt-get -y --no-install-recommends -o Dpkg::Options::=--force-confold install /tmp/current/*.deb
for name in $packages; do
    check_installed "$name"
    test "$(dpkg-query -W -f='${Version}' "$name")" = "$version"
done
sha256sum -c /tmp/preserve.sha256
sha256sum -c /tmp/os-release.sha256
dpkg-query -S "$skel" /usr/share/kernova/product.json /usr/bin/kernova-welcome
test -x /usr/share/kernova/diagnostics/check-session
test -r /usr/share/doc/kernova-welcome/user-guide.md
test -r /usr/share/plasma/look-and-feel/org.kernova.night/contents/layouts/org.kde.plasma.desktop-layout.js
desktop-file-validate /usr/share/applications/kernova-welcome.desktop /etc/xdg/autostart/kernova-welcome-autostart.desktop
kpackagetool6 --type Plasma/LookAndFeel --show org.kernova.night
kpackagetool6 --type Wallpaper/Images --show /usr/share/wallpapers/Parallax
test -s /usr/share/wallpapers/Parallax/contents/images/3840x2160.png
kpackagetool6 --type KWin/Script --show org.kernova.windowtools
python3 -c 'from PySide6 import QtCore, QtGui, QtWidgets'
python3 - "$version" <<'PY'
import configparser
import json
from pathlib import Path
import sys
assert json.loads(Path("/usr/share/kernova/product.json").read_bytes())["version"] == sys.argv[1]
associations = configparser.ConfigParser(interpolation=None)
associations.read("/etc/skel/.config/mimeapps.list")
for mime, apps in associations["Default Applications"].items():
    handler = Path("/usr/share/applications") / apps.rstrip(";")
    assert handler.is_file(), f"{mime} handler missing: {handler}"
PY

echo 'Removing and purging cosmetics while retaining the desktop metapackage'
apt-get -y remove kernova-branding kernova-default-settings kernova-welcome
test -f "$skel"
test ! -e /usr/share/kernova/product.json
sha256sum -c /tmp/preserve.sha256
apt-get -y purge kernova-branding kernova-default-settings kernova-welcome
test ! -e "$skel"
test -f "$newhome/.config/kdeglobals" && test -f "$originalhome/.config/kdeglobals"
for name in $core; do check_installed "$name"; done
apt-get --simulate autoremove > /tmp/removal-plan
for name in $core; do
    if grep -Eq "^Remv ${name}( |$)" /tmp/removal-plan; then
        echo "Unexpected desktop autoremoval: $name" >&2
        exit 1
    fi
done
apt-get check
sha256sum -c /tmp/os-release.sha256
echo 'PASS: package upgrade, identity, conffiles, per-user settings, KDE theme discovery and removal.'
