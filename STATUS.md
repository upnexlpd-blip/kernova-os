# KERNOVA OS 0.1.0 development preview — source handoff

**18 November 2026.** The build project, package sources, native desktop application, test runner and documentation are ready for the first Debian build. No ISO or KERNOVA .deb was produced. No live, installed or updated guest has booted in this session. The source archive and its transfer checksum are in artifacts/. The archive excludes build tools, caches and virtual disks.

## Milestones

| Milestone | Implemented | Executed and observed | Remaining gate |
| --- | --- | --- | --- |
| A. Foundation | Preflight, prerequisite installer, clean Debian live-build work tree, KDE foundation profile, GRUB BIOS and UEFI, firmware selection | Inspected Windows host; authenticated Debian metadata and installer inputs; verified the configuration with trixie live-build's upstream scripts. The native Linux build gate exited 1 on Windows. | Build foundation on Debian, validate the actual ISO, then boot to Plasma. |
| B. Desktop | Four Debian package sources, Night and Parallax, Breeze light alternative, default associations, native bilingual Welcome and everyday app selection | Ownership and package availability inspected. Windows source suite passed, including 13 Welcome tests. All six Qt tests passed again at 2×. ShellCheck and desktop-file-validate passed. | Build and inspect the Debian packages; boot the full preview and check real Plasma, login, panel, scaling, apps and devices. |
| C. Installation | Authenticated Debian Installer inputs, interactive live installer in GRUB, fresh private disk and media-detached QEMU paths, installed-session checks | Verified installer hashes, menu/configuration source, VM argument and storage tests. No virtual disk installation performed. | Install by hand under each firmware profile. Check personal login, bootloader, persistence and removal of live credentials. |
| D. Maintenance | Isolated package lifecycle test, local update path, APT/security setup, backup/recovery guidance, enforced-key firmware selector | Checked selected dependency names, package ownership and OVMF descriptors. The lifecycle entry point reported its Linux requirement on Windows. | Exercise package install/upgrade/removal, reboot after an actual update, restore a backup and verify independent machine identities. |
| E. Handoff | Source tarball with Linux executable modes, Macedonian quick start, release evidence format and verification matrix | Windows checks recorded below. This source archive has a SHA-256 sidecar. | Generate an ISO, validate its contents/checksum, and attach independently observed guest evidence before release. |

## Executed evidence

- [Source checks](docs/evidence/windows-source.txt) and [Qt at double scale](docs/evidence/windows-qt-2x.txt).
- [Build configuration and authenticated installer inputs](docs/evidence/iso-recipe.txt), [archive signature verification](docs/evidence/trixie-signatures.txt), [package names, versions and firmware selection](docs/evidence/archive-audit.txt), and [ownership audit](packages/README.md).
- [Windows inventory and blocked commands](docs/evidence/windows-builder.txt). Host OS was Windows 11 Pro x64. WSL is absent, firmware virtualization is reported off, and the environment lacks Linux live-build, mount/chroot facilities and an installed guest runner. The user chose to keep the handoff in the workspace.
- [Full verification matrix and runtime procedures](docs/verification.md). Package solving, service health, firmware enforcement, boot, installation and update results require a running Debian build and a real guest session.

## Resume from here

Read [START_HERE_MK.md](START_HERE_MK.md) to transfer the source to the Debian builder. After extracting under ~/kernova-os on ext4, use these commands in the builder:

```sh
cd ~/kernova-os
sudo ./scripts/install-prerequisites
./scripts/preflight
./scripts/check-source
./scripts/build-iso foundation
```

Boot the printed foundation ISO in a newly created test VM. Then run `./scripts/build-iso preview` and `./scripts/test-packages`. Follow [the VM installation procedure](docs/install.md) through detached and post-update boots. Record the release directory, checksum and the first failing stage or observed success. Keep failed build logs and the previous validated release.

The source archive is a private development handoff. Production signing, distribution, physical installation and dual boot have no release evidence.
