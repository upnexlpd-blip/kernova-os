# Architecture and configuration

The preview targets Debian 13 trixie on amd64. Debian supplies the kernel and initramfs, systemd, udev, APT, KDE Plasma 6.3 and the applications. Live-build produces an ISO with GRUB paths for BIOS and UEFI and a compressed SquashFS. Debian Installer's live mode copies that customized filesystem to the selected guest disk. The boot menu starts d-i with its own kernel. There is no desktop partitioning utility or installer launcher. [Debian trixie](https://www.debian.org/releases/trixie/), [live-build configuration](https://manpages.debian.org/trixie/live-build/lb_config.1.en.html), [Debian live installer](https://live-team.pages.debian.net/live-manual/html/live-manual/customizing-installer.en.html)

| Component | Provider and policy |
| --- | --- |
| Kernel and boot | Debian linux-image-amd64, initramfs-tools and live-boot. Strict signed EFI build setting. Normal and failsafe live boot parameters are separate. |
| Desktop | Plasma Wayland, SDDM, Xwayland for compatible clients, Breeze controls and upstream Plasma panel. Guest testing determines session support. |
| Devices | NetworkManager, plasma-nm, BlueZ/Bluedevil, PipeWire/WirePlumber and plasma-pa. Firmware is drawn from main and non-free-firmware. |
| Software | APT/dpkg for system packages, Discover with Debian's PackageKit backend. Repositories use trixie, trixie-updates and trixie-security with signature checks. |
| Trust boundary | Ordinary user for source and application work. A privileged live-build child in a private mount namespace inside the dedicated builder. A chroot shares its host kernel. |
| Identity | Debian base-files retains ownership of both os-release paths. KERNOVA identity lives at /usr/share/kernova/product.json. Existing applications and update tools can continue to identify the Debian base. [os-release specification](https://www.freedesktop.org/software/systemd/man/latest/os-release.html) |

## Package ownership

- **kernova-branding** owns the original logo, wallpaper, color scheme, Plasma look-and-feel package and product metadata.
- **kernova-default-settings** seeds new homes through /etc/skel/.config and supplies the read-only guest diagnostic. KDE branding code does not rewrite existing home directories during an upgrade.
- **kernova-welcome** installs the native PySide6 application, icon integration, desktop launcher, KDE autostart entry and local guide. The per-user sign-in preference is held by QSettings. Actions pass fixed arguments to normal desktop tools.
- **kernova-desktop** depends on the actual desktop stack and everyday apps. Optional branding relationships allow the cosmetics to be removed while the metapackage keeps Plasma and its runtime dependencies installed.

Use `dpkg-query -S /etc/os-release /usr/lib/os-release /usr/share/kernova/product.json` on a full installed preview to inspect ownership. SDDM theming and a custom boot splash are deferred until basic boot is verified.

## Change a default

| Change | Authoritative input |
| --- | --- |
| Product name, ISO slug, version, release channel, default live locale | product.json. Match the version in packages/debian/changelog. Keep package names and stable desktop IDs intact for existing installations. If renaming the branded application as well, update the English/Macedonian catalog and both .desktop entries. |
| Dark palette and focus colors | branding/KernovaNight.colors |
| Wallpaper and logo | branding/Parallax/parallax.svg and branding/kernova-logo.svg. The Debian rules generate the installed PNG wallpaper from the SVG. |
| Plasma theme wiring | branding/org.kernova.night/contents/defaults and packages/defaults/kdeglobals. Existing users can select KERNOVA Night or Breeze in System Settings. |
| Default applications and associations | packages/debian/control under kernova-desktop; packages/defaults/mimeapps.list for MIME handlers. Keep the validator's required release checks consistent with intentional changes. |
| Foundation and firmware packages | config/package-lists/base.list.chroot. Live-only components use the chroot_live list so the installer can remove them from the target. |
| Welcome wording | apps/welcome/locales/en.json and mk.json. Missing translations fall back to English. |
| Boot options, archive components and ISO settings | auto/config. The builder accepts only the supported suite/architecture and checks the installed live-build manual and usage. An archive component expansion requires documenting the package, origin and redistribution conditions. |

The foundation build selects Debian's KDE session and installer. The preview adds the four KERNOVA packages. Changing the locale in product.json sets the default live locale; the interactive installer asks for the installed locale. The supported profiles use signed Debian sources, without a KERNOVA network repository, telemetry service, SSH server or custom privileged daemon. The package and socket inventory of the first real guest must still be reviewed. [Debian Live Manual](https://live-team.pages.debian.net/live-manual/html/live-manual.en.html) and [Plasma theme documentation](https://develop.kde.org/docs/plasma/)
