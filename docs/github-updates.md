# Get KERNOVA updates in Discover

KERNOVA 0.1.3 includes the public signing key and package source. In an installed Plasma session, Discover periodically checks for updates and shows a notification when a newer package is available. Open **Discover â†’ Updates** to review and install it. A GitHub account is unnecessary.

## Install Smart Performance 0.1.4

On an installed KERNOVA 0.1.3 desktop, connect to the internet and wait for the Discover notification, or open **Discover > Updates > Refresh**. Select **Update All**, authenticate and open **KERNOVA Performance Center** from the application menu. To verify the installed release, run `dpkg-query -W kernova-desktop kernova-performance`.

## Connect an existing 0.1.2 installation

Open Konsole on the installed system and run the following commands once. They verify the downloaded source configuration, register the archive and remove the old installer-only entry from the installed system. Your account and files stay in place.

```sh
(
  set -e
  work=$(mktemp -d)
  cd "$work"
  curl -fsSL https://raw.githubusercontent.com/upnexlpd-blip/kernova-linux/apt/kernova.sources -o kernova.sources
  echo '5501daf88da0afff004ba7c034792f76cb847f6382e0e277b3439d2f05a71fdf  kernova.sources' | sha256sum -c -
  sudo install -m 0644 kernova.sources /etc/apt/sources.list.d/kernova.sources
  if ! grep -qw 'boot=live' /proc/cmdline; then
    sudo sed -i '/^deb \[trusted=yes\] file:\/run\/live\/medium trixie main non-free-firmware$/d' /etc/apt/sources.list
  fi
  sudo apt-get update --error-on=any
)
```

Open **Discover â†’ Updates**. Check the candidate version with `apt-cache policy kernova-desktop`. Changes made in a regular Live session are temporary.

## Publish a release

Increase the version in `product.json` and `packages/debian/changelog` and push the release to the main branch of kernova-os. For 0.1.4, GitHub Actions promotes the five tested Debian packages, verifies them against the approved release manifest, signs the stable index and publishes it on the apt branch of kernova-linux. Every Monday it renews the indexes using the original packages. Live-only changes, such as boot menus, ship on new installation media.

The primary key fingerprint is `7656 A706 E55A 3F68 686D E0FD B9EF 5C29 B220 41E8`. Renew the signing subkey before November 2029 and distribute the refreshed public key through the current trusted channel. The primary private key stays outside GitHub. The publishing workflow uses GitHub Actions secrets for the signing subkey and the package repository deploy key.
