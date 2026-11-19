# KERNOVA OS development preview

## Viber popup placement on Plasma Wayland, 0.1.13

An installed 0.1.10 desktop upgraded to the five signed 0.1.13 testing packages. Running the session's catalog initializer applied the per-account platform preference to the existing Flathub Viber installation. Rakuten Viber then opened using XWayland, verified by its mapped ViberPC window. A frameless Qt test popup was centered on native Wayland. With the backend selected for Viber, it appeared at the requested (717, 650) on a 1024 by 768 screen, 12 pixels from the right and above the panel. Testing covered window placement and Viber startup. An incoming message on a linked Viber account still needs confirmation. [Placement test](docs/evidence/viber-0.1.13/placement.png)

## Desktop update 0.1.10 and USB release 0.1.8

The 0.1.8 Live image booted into KDE Plasma with SeaBIOS and as a read-only USB device with UEFI. With networking disconnected, Calamares installed to an empty 48 GiB virtual disk. The new account signed in after the USB was detached. All five KERNOVA packages reported version 0.1.8 on disk. The ISO contains 1,301 packages. Both internal checksum lists and the exported ISO SHA-256 were verified. [Completed installation](docs/evidence/usb-0.1.8/offline-install.png) · [Installed versions](docs/evidence/usb-0.1.8/installed-packages.png)

The 0.1.10 package update adds logos to AI Tools and displays installer output in the window. Installed command-line tools offer an **Open in Konsole** action. The Plasma session applies the bottom-right notification default at the next login and retains individual position preferences. A standard desktop notification was tested in an upgraded Wayland session. [AI Tools and notification](docs/evidence/desktop-0.1.10/ai-tools-notification.png)

On the freshly installed 0.1.8 disk, Discover offered all five 0.1.10 packages from the public stable channel. **Update All** installed them in the running session. All five versions were confirmed with `dpkg-query` and `dpkg --audit` reported no pending issues. [Discover update list](docs/evidence/desktop-0.1.10/discover-updates.png)

## KERNOVA Torrent and Steam startup, 19 November 2026

On an installed KERNOVA Plasma guest (amd64 UEFI, QEMU WHPX, 4 GiB), double-clicking Debian's official 13.7.0 netinst torrent in Dolphin opened the download dialog. The client saved 151 pieces before shutdown. After a fresh boot of the same disk and login, the queue resumed automatically, advanced to 1,563 saved pieces and finished all 3,024. The 756 MiB image matched Debian's published SHA-512. The QEMU process was relaunched after WHPX paused on warm reset. The separate magnet transfer used a local test peer, passed a byte comparison and retained its file when removed. The final icon revision reopened the completed ISO in the same queue. [Before shutdown](docs/evidence/torrent-0.1.7/before-restart.png) · [After login](docs/evidence/torrent-0.1.7/after-restart.png) · [Magnet](docs/evidence/torrent-0.1.7/magnet.png) · [Integrity](docs/evidence/torrent-0.1.7/checksum.png) · [Final client](docs/evidence/torrent-0.1.7/completed.png)

A fresh Steam Flatpak installation waited for a controller-rules warning on the original desktop. After acknowledgment it downloaded the client and reached sign-in. On 0.1.7, Debian's steam-devices package was present. Launching Steam from KDE after reboot reached sign-in directly. Testing ended at sign-in. [Menu entry](docs/evidence/torrent-0.1.7/steam-menu.png) · [Steam sign-in](docs/evidence/torrent-0.1.7/steam-login.png)

A second installed 0.1.6 guest received 0.1.7 through **Discover > Updates > Refresh > Update All** with the testing source disabled. All five installed versions matched the verified stable packages. This account installed Steam from Flathub using Discover. Before reboot, Steam still warned about input-device access. The tester left the warning unacknowledged and restarted the system. After reboot the account and Steam sandbox could write to the input device, and the fresh client completed both first-run downloads and opened sign-in. [Discover upgrade](docs/evidence/torrent-0.1.7/discover.png) · [Installed versions and input access](docs/evidence/torrent-0.1.7/installed-versions.png) · [Steam installation](docs/evidence/torrent-0.1.7/steam-installed.png) · [First download](docs/evidence/torrent-0.1.7/steam-download.png) · [Client update](docs/evidence/torrent-0.1.7/steam-client-update.png) · [Sign-in after the stable update](docs/evidence/torrent-0.1.7/stable-steam-login.png)

## Windows program support 0.1.6, 19 November 2026

An installed KERNOVA 0.1.5 Plasma VM previously opened the application chooser for the official OpenTTD 15.3 Windows x64 installer. After upgrading the five KERNOVA packages, a fresh unprivileged account double-clicked the same installer in Dolphin, confirmed Execute and completed the original installation wizard with its defaults. The launcher fetched the Wine 11.0 Flatpak for the account. Opening **Windows Programs → OpenTTD/OpenTTD** launched the Windows game. After consenting to the game's OpenGFX download, the tester generated a map and placed track. The game charged £90. [Before the update](docs/evidence/windows-games-0.1.6/before.png) · [First launch](docs/evidence/windows-games-0.1.6/first-open.png) · [Installation](docs/evidence/windows-games-0.1.6/installed.png) · [Shortcut](docs/evidence/windows-games-0.1.6/start-menu.png) · [Gameplay](docs/evidence/windows-games-0.1.6/gameplay.png)

The test used QEMU on Windows with WHPX, UEFI, two virtual CPUs, 4 GiB RAM and software rendering. The installer SHA-256 was `f061a7fd16ebe682edd45b02d048f068735a4a296c2b2b325246b10e01c748bf`. OpenTTD's Windows MIDI initialization hung in the first candidate. The launcher selects the game's null MIDI driver for OpenTTD. Sound effects, hardware GPU performance and other games remain unverified.

A second installed 0.1.5 VM using the public stable channel received all five 0.1.6 packages in Discover. After **Update All**, the installed package versions and the default Windows executable handler matched the release. The signed stable index and all five published package hashes matched the gameplay-tested build. [Discover update](docs/evidence/windows-games-0.1.6/discover.png) · [Installed versions and default handler](docs/evidence/windows-games-0.1.6/versions.png)

## Stable package update 0.1.5, 19 November 2026

The Welcome application bundles eight Papirus app icons for offline use. The branding package adds seven photographs, bringing the KERNOVA photo collection to ten 3840×2160 wallpapers. Each wallpaper includes its photographer and source in its KDE metadata. An installed 0.1.4 Plasma VM upgraded through Discover and displayed all eight icons and ten wallpaper previews. [Discover](docs/evidence/artwork-0.1.5/discover.png) · [App catalog](docs/evidence/artwork-0.1.5/welcome-apps.png) · [Desktop shortcuts](docs/evidence/artwork-0.1.5/welcome-shortcuts.png) · [Wallpaper chooser](docs/evidence/artwork-0.1.5/wallpaper-chooser.png)

## Stable package update 0.1.4, 19 November 2026

Smart Performance 0.1.4 is available from the existing stable APT channel. The five package hashes match the tested GitHub prerelease. The published index was independently verified with the key embedded in 0.1.3. On an installed UEFI guest, APT showed 0.1.3 installed and 0.1.4 available from the stable source. Discover installed all five packages through **Update All**, and dpkg confirmed their versions. [Stable release](https://github.com/upnexlpd-blip/kernova-os/releases/tag/v0.1.4) · [APT origin](docs/evidence/performance/stable-origin.png) · [Discover](docs/evidence/performance/stable-discover.png) · [Installed versions](docs/evidence/performance/stable-installed.png)

## Local release 0.1.3, 19 November 2026

The 2,380,533,760-byte ISO includes the signed public KERNOVA APT source for Discover. SHA-256 is `4f265639182cb409d4e22eb3ca8a472eaa69d7a5a5672a56b2d026fdbeed43da`. Windows verified the write to a physical Kingston DataTraveler 3.0 by reading it back and safely ejected the stick. [Local ISO](artifacts/20261119T112142Z-preview/kernova-os-0.1.3-amd64.iso) · [Build validation](artifacts/20261119T112142Z-preview/validation.log) · [USB record](docs/evidence/updates/kingston-0.1.3.txt)

In a fresh UEFI Live session, APT used the Debian HTTPS sources and fetched the signed KERNOVA index. Its list of download targets contained no Live-medium URLs. A separate installed 0.1.2 guest received the Plasma update notification and upgraded all four KERNOVA packages to 0.1.3 through Discover after the one-time channel setup. [Live sources](docs/evidence/updates/live-sources-0.1.3.png) · [Discover upgrade](docs/evidence/updates/discover-0.1.3.png) · [Channel setup for older installations](docs/github-updates.md)

Calamares installed 0.1.3 on a fresh 48 GiB virtual disk. After booting that disk with the ISO detached and signing in, `sudo apt-get update --error-on=any` refreshed Debian, Debian Security, Debian Updates and KERNOVA successfully. [Installer finish](docs/evidence/updates/install-0.1.3.png) · [Installed APT refresh](docs/evidence/updates/installed-refresh-0.1.3.png)

## Local release 0.1.2, 19 November 2026

The installer opens directly from the active local live desktop. In a fresh UEFI guest, opening the desktop icon brought up Calamares without entering credentials. The Users page accepted a new personal password and advanced to the installation summary. The new ISO is 2,380,527,616 bytes. SHA-256: `a9bd4661490ea15a56625fc6432df1b27517cbca2e646aa5052f477a8c401e20`. [ISO](artifacts/20261119T093631Z-preview/kernova-os-0.1.2-amd64.iso) · [Validation](artifacts/20261119T093631Z-preview/validation.log) · [Installer](artifacts/20261119T093631Z-preview/live-evidence/installer/launcher-opens-wizard.png) · [Users page](artifacts/20261119T093631Z-preview/live-evidence/installer/users-personal-password.png)

Calamares completed the installation on the guest's 48 GiB disk. After detaching the ISO, the guest booted in UEFI mode and reached the installed Plasma desktop with the password set on Users. The physical Kingston DataTraveler was written and verified by read-back. [Installed session](artifacts/20261119T093631Z-preview/live-evidence/installer/installed-desktop.png) · [USB verification](artifacts/20261119T093631Z-preview/live-evidence/installer/kingston-write.txt)

## Local release 0.1.1, 19 November 2026

The Debian builder produced the full 2,380,523,520-byte preview with 1288 installed packages. All 36 source tests passed after fixing a GRUB menu URI that Debian live-build shortened. Both internal checksum lists verified against the mounted final image, including the GRUB files modified during ISO mastering. Windows independently verified SHA-256 `0d8731622c7c46367f0184fa65d3ee404692b082d3e31bb0d7df283c755f245f`. The export includes four separately hashed KERNOVA update packages. [ISO](artifacts/20261119T020026Z-preview/kernova-os-0.1.1-amd64.iso) · [Validation](artifacts/20261119T020026Z-preview/validation.log) · [Packages](artifacts/20261119T020026Z-preview/packages) · [Matching build source](artifacts/kernova-os-0.1.1-source.tar.gz)

The 01:47 UTC build launches Calamares and accepts the temporary live password. Its user-creation page found no password-quality dictionary. The 02:00 UTC build adds a tested Debian dictionary to the ISO. A complete installed-disk boot with Calamares on this build still needs verification.

The 02:00 UTC ISO booted as a removable USB device under enrolled Debian OVMF and reached KERNOVA Welcome in Plasma. The kernel reported SecureBoot=1, SetupMode=0 and integrity lockdown. The live medium was /dev/sda, USB, removable and read-only. [Desktop](artifacts/20261119T020026Z-preview/live-evidence/secure-usb/live-desktop.png) · [Firmware and USB checks](artifacts/20261119T020026Z-preview/live-evidence/secure-usb/guest-verification.png)

KDE Discover uses a signed per-user Flathub source. In the preceding full Preview, Chrome, Viber, Telegram and ZapZap were installed and launched through Discover. Large guest downloads completed for Viber and Telegram with an emulated e1000e Ethernet adapter and IPv4-only QEMU NAT. The physical system's network configuration is independent. [Application checks](artifacts/20261119T005030Z-preview/live-evidence/discover-smoke/check.md)

Discover checks for package updates. Connecting a KERNOVA repository on a VPS requires its HTTPS URL and signing-key fingerprint. The Debian tests exercised release signing and rejection of modified metadata. [VPS instructions](docs/vps-updates.md)

## Foundation installation and hardware checks, 19 November 2026

The graphical Debian Installer booted in UEFI mode and installed the foundation system into the free space of a private 48 GiB virtual disk. Its final confirmation listed only the three new partitions for formatting. After the ISO was removed, the guest booted from its own EFI loader and reached Plasma. A file on the original FAT16 partition retained the same SHA-256 after the installation. This test used a synthetic data partition. Booting a pre-existing Windows installation requires a separate test. [Install record](artifacts/20261118T231642Z-foundation/live-evidence/uefi-install-check.txt) · [Partition confirmation](artifacts/20261118T231642Z-foundation/live-evidence/uefi-installer-format-confirmation.png) · [File verification](artifacts/20261118T231642Z-foundation/live-evidence/uefi-installed-sentinel.png)

The foundation kernel also booted from emulated read-only optical and removable USB media using Debian OVMF with enrolled Secure Boot keys. Both guests read `SecureBoot=1` and `SetupMode=0` from EFI variables and reported kernel integrity lockdown. [Firmware, commands and screenshots](docs/evidence/foundation-secure-boot.md)

The accelerated Live guest obtained a wired connection and successfully requested the Debian archive over HTTPS. The Windows host has an Intel I211 Ethernet adapter and a Realtek 0bda:8771 USB Bluetooth controller. The Live filesystem contains the RTL8761BU firmware and configuration. Pairing and Wi-Fi association require exposed physical radios. [Network check](artifacts/20261118T231642Z-foundation/live-evidence/whpx-wired-https.png) · [Firmware check](artifacts/20261118T231642Z-foundation/live-evidence/whpx-firmware-wallpapers.png)

The original foundation profile omitted the KDE image thumbnail worker. After loading the Debian KIO worker and its image plugins in the running Live account, the wallpaper chooser rendered all three KERNOVA photographs and the stock Nuvole thumbnail. The source now requires `kio-extras` for future foundation and preview images. [Wallpaper chooser](artifacts/20261118T231642Z-foundation/live-evidence/wallpaper-thumbnails-fixed.png)

## Windows-hosted Debian build

On 19 November 2026 the dedicated Debian 13 amd64 builder finished the first foundation ISO. The builder passed the privileged preflight and all 24 source tests. Validation verified the kernel, initramfs, Live filesystem, package manifest, signed installer inputs, EFI signature tables and two boot entries. Windows verified the SHA-256 after transfer. The builder shut down cleanly. Its 80 GiB disk is at `D:\KERNOVA-VM\debian13-builder\debian13.qcow2`. [Debian transcript](docs/evidence/debian-builder.txt) · [Local builder and Live instructions](docs/windows-builder.md)

The local ISO is 2,117,629,952 bytes. SHA-256 is `52ab0d7191c4c730f3da23651272e5f23d8c660398ae75a64f8a33c54d46942b`. [ISO](artifacts/20261118T231642Z-foundation/kernova-os-0.1.0-amd64.iso) · [Manifest](artifacts/20261118T231642Z-foundation/packages.tsv) · [Build and validation logs](artifacts/20261118T231642Z-foundation)

## Original source handoff

**18 November 2026.** The source archive used for the foundation build is in `artifacts/` with its transfer checksum. It contains the package sources, native desktop application, test runner and documentation. Generated media and virtual disks are stored separately.

## Milestones at the first foundation handoff

| Milestone | Implemented | Executed and observed | Remaining gate |
| --- | --- | --- | --- |
| A. Foundation | Debian 13, KDE Plasma, live-build and installer | Built and validated the foundation ISO. Booted its BIOS Live entry in a visible diskless VM and opened Dolphin with Meta+E. [Screenshot](artifacts/20261118T231642Z-foundation/live-evidence/plasma-dolphin.png) | UEFI runtime boot and the broader device checks remain open. |
| B. Desktop | Four Debian package sources, Night and Parallax, Breeze light alternative, default associations, native bilingual Welcome and everyday app selection | Ownership and package availability inspected. Windows source suite passed, including 13 Welcome tests. All six Qt tests passed again at 2×. ShellCheck and desktop-file-validate passed. | Build and inspect the Debian packages; boot the full preview and check real Plasma, login, panel, scaling, apps and devices. |
| C. Installation | Authenticated Debian Installer inputs, interactive live installer in GRUB, fresh private disk and media-detached QEMU paths, installed-session checks | Verified installer hashes, menu/configuration source, VM argument and storage tests. No virtual disk installation performed. | Install by hand under each firmware profile. Check personal login, bootloader, persistence and removal of live credentials. |
| D. Maintenance | Isolated package lifecycle test, local update path, APT/security setup, backup/recovery guidance, enforced-key firmware selector | Checked selected dependency names, package ownership and OVMF descriptors. The lifecycle entry point reported its Linux requirement on Windows. | Exercise package install/upgrade/removal, reboot after an actual update, restore a backup and verify independent machine identities. |
| E. Handoff | Source tarball, Quick start and evidence matrix | Published the foundation ISO, SHA-256, manifest, build and validation logs locally. | Build and verify the branded preview and its installed system. |

## Executed evidence

- [Source checks](docs/evidence/windows-source.txt) and [Qt at double scale](docs/evidence/windows-qt-2x.txt).
- [Build configuration and authenticated installer inputs](docs/evidence/iso-recipe.txt), [archive signature verification](docs/evidence/trixie-signatures.txt), [package names, versions and firmware selection](docs/evidence/archive-audit.txt), and [ownership audit](packages/README.md).
- [Initial Windows inventory](docs/evidence/windows-builder.txt). Windows 11 Pro x64 reported firmware virtualization disabled. The local builder and Live VM use portable QEMU with software emulation.
- [Full verification matrix and runtime procedures](docs/verification.md).

## Resume from here

The project is already on ext4 in the local Debian builder. Use the ordinary build account for the full preview and package lifecycle checks:

```sh
cd ~/kernova-os
./scripts/preflight
./scripts/build-iso preview
./scripts/test-packages
```

Boot the preview in a new test VM and follow [the installation procedure](docs/install.md) through detached and post-update boots. Record the release directory, checksum and first failing stage or observed success. Keep the validated foundation ISO.

The source archive is a private development handoff. Production signing, distribution, physical installation and dual boot have no release evidence.
