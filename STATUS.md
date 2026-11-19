# KERNOVA OS development preview

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
