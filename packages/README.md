# Maintaining the KERNOVA packages

The four architecture-independent binaries share the native Debian source package `kernova-components`. Build them as your ordinary user in the Debian 13 builder. From the project root, pass a new or empty directory for the binaries.

```sh
./scripts/build-packages artifacts/packages-0.1.0
```

The builder uses debhelper compatibility level 13 and `dpkg-buildpackage`. It retains the Debian source archive, `.dsc`, `.buildinfo`, `.changes`, binary packages and `build.log` under the printed `build/packages-…` directory. It publishes all four binaries to the output directory after checking their package names, versions and architectures. Private development builds are unsigned. The four `.deb` files can be installed together on the disposable KERNOVA guest using APT.

```sh
sudo apt install ./kernova-*.deb
```

Run that guest command from a directory containing only the intended four local packages. APT obtains dependencies using the guest’s configured Debian archives. To release a newer local version, edit `product.json`, create a matching new entry at the top of `packages/debian/changelog`, then repeat the build with a new output directory. The builder stops on a version mismatch.

| Package | Owned files and behavior |
| --- | --- |
| `kernova-branding` | Product metadata in `/usr/share/kernova/product.json`, hicolor SVG icon, KERNOVA Night global theme, color scheme and Parallax wallpaper. |
| `kernova-default-settings` | Initial `kdeglobals` and `mimeapps.list` under `/etc/skel/.config` and the guest session diagnostic. Debian account creation copies the skeleton. Subsequent package changes leave existing home directories to their owners. |
| `kernova-welcome` | Ordinary-user launcher, application and autostart entries, native Python/Qt application, translation catalogs and offline Markdown guide. |
| `kernova-desktop` | Depends on the Plasma session, device support, Discover/PackageKit and everyday applications. It recommends the three KERNOVA customization packages. The preview ISO explicitly selects all four. Removing cosmetics keeps the metapackage and core desktop dependencies. |

## Appearance and file ownership

Edit `branding/KernovaNight.colors` for the palette. It defines foregrounds, surfaces, links, selection and focus colors. Edit `branding/Parallax/parallax.svg` for the wallpaper. The package build renders a 3840 × 2160 PNG and a thumbnail with Debian’s librsvg. Both assets and the `branding/kernova-logo.svg` mark are original KERNOVA work under the project MIT license.

The new-account skeleton selects `org.kernova.night`. Plasma 6.3 reads the global theme at startup. Its `contents/defaults` names the color scheme and the `Parallax` wallpaper package. A link uses the installed Breeze Dark layout script, which provides Plasma’s standard panel. Breeze supplies the widget style, icons and decoration under its upstream package licenses. To use a light desktop, choose **Breeze** in System Settings → Colors & Themes → Global Theme. To change only the palette, select a light color scheme under Colors. Plasma’s animation speed is user-adjustable in Quick Settings. [KDE global theme locations](https://develop.kde.org/docs/plasma/) · [Plasma 6 theme format](https://develop.kde.org/docs/plasma/theme/theme-porting-to-plasma6/) · [Trixie Plasma startup](https://sources.debian.org/src/plasma-workspace/4%3A6.3.6-2/startkde/startplasma.cpp/) · [Trixie wallpaper lookup](https://sources.debian.org/src/plasma-workspace/4%3A6.3.6-2/libkworkspace/defaultwallpaper.cpp/) · [Installed Breeze resources](https://packages.debian.org/trixie/all/plasma-workspace-data/filelist)

The first preview preserves Debian’s system identity. Debian `base-files` owns both `/etc/os-release` and `/usr/lib/os-release`. KERNOVA ships its metadata in a separate path and relies on Debian’s SDDM and boot configuration. File associations for new accounts live in `packages/defaults/mimeapps.list`. Change the desktop application selection in `packages/debian/control`. Trixie’s `plasma-discover` package includes the PackageKit plugin. [Debian base-files inventory](https://packages.debian.org/trixie/amd64/base-files/filelist) · [OS identity specification](https://www.freedesktop.org/software/systemd/man/latest/os-release.html) · [Discover plugin inventory](https://packages.debian.org/trixie/amd64/plasma-discover/filelist)

### Ownership audit for 0.1.0

On 18 November 2026, the Windows development host compared both Debian trixie `main` Contents inventories against the SHA-256 values in the signed release metadata. The skeleton files, KERNOVA autostart and application entry, launcher, icon, palette, global theme, wallpaper and product data paths had no Debian file owners in these inventories. Both OS identity paths belonged to `base-files`. Plasma’s Wayland session, the referenced Breeze Dark layout, the Breeze light theme and the Discover PackageKit plugin were present. The archive index also resolved all 53 external package or build dependency names, including the virtual debhelper compatibility and Python helper packages. Security updates can change versions between builds. The package build’s `.buildinfo` and the ISO build’s package manifest record the versions actually used.

| Signed index | SHA-256 |
| --- | --- |
| `main/Contents-all.gz` | `0c2e2d099588073221d6eebb0a84e950f1728818faf527de9034d0116f7a8221` |
| `main/Contents-amd64.gz` | `3d3e6930908db0b53f780dd7397b9589e27db88b59205c331a76d76d6726e419` |
| `main/binary-amd64/Packages.xz` | `7778d3e3f303b7ddb8ce0fe7c8d57473a076c6bf2e8f241f75421d2396352498` |

To recheck the file paths, use the matching authenticated Contents files from the official trixie archive and run the following in their download directory. The output identifies the upstream paths and any new collisions. An APT install in the disposable test chroot checks the actual selected package set. [Debian trixie main indexes](https://deb.debian.org/debian/dists/trixie/main/) · [Recorded release signature check](../docs/evidence/trixie-signatures.txt)

```sh
zcat Contents-all.gz Contents-amd64.gz | awk '
  $1 ~ /^(etc\/os-release|usr\/lib\/os-release|etc\/skel\/\.config\/(kdeglobals|mimeapps\.list))$/ ||
  $1 ~ /^(usr\/bin\/kernova-welcome|etc\/xdg\/autostart\/kernova-|usr\/share\/(kernova\/|applications\/kernova-|icons\/hicolor\/scalable\/apps\/kernova-|color-schemes\/KernovaNight\.colors|plasma\/look-and-feel\/org\.kernova\.night\/|wallpapers\/Parallax\/))/ ||
  $1 ~ /^(usr\/share\/wayland-sessions\/plasma\.desktop|usr\/share\/plasma\/look-and-feel\/org\.kde\.breezedark\.desktop\/contents\/layouts\/org\.kde\.plasma\.desktop-layout\.js|usr\/lib\/x86_64-linux-gnu\/qt6\/plugins\/discover\/packagekit-backend\.so)$/ {print}'
```

## Package lifecycle verification

Run the lifecycle check as an ordinary user in the dedicated Debian 13 amd64 builder. It needs network access to signed Debian archives, the build prerequisites, `mmdebstrap`, `uidmap`, working unprivileged user namespaces and subordinate UID/GID mappings for the builder account. A fresh chroot downloads the full desktop dependency set. Allow several gigabytes of free space in the build and temporary directories.

```sh
./scripts/test-packages
```

The check builds two sets of packages. The older version is a clearly marked local test fixture, with an earlier Debian version and a changed skeleton conffile. APT installs that fixture, upgrades to the actual version, removes the cosmetics and purges their conffiles. The checks cover the existing user, a newly initialized user, a locally modified conffile, upstream OS identity, theme and launcher discovery, file association targets, and the desktop’s continued presence in APT’s simulated autoremove plan. The command retains its inputs and result log under `build/lifecycle-…`. A full desktop login, graphical behavior and reboot after an update need the separate installed-VM procedure. [Debian mmdebstrap manual](https://manpages.debian.org/trixie/mmdebstrap/mmdebstrap.1.en.html)

To inspect packaging warnings in the dedicated builder, install `lintian` and pass it the `.changes` file from the printed build directory. Review its findings before distribution. The Debian copyright notices for external software and firmware remain in their respective packages.
