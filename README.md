# KERNOVA OS

Personal Debian 13 amd64 desktop with KDE Plasma. The current local development preview is **0.1.2**. It includes KDE Discover, the KERNOVA Welcome and AI Tools applications, hardware settings, three photographic wallpapers and the graphical Calamares installer. [Preview ISO](artifacts/20261119T093631Z-preview/kernova-os-0.1.2-amd64.iso) · [SHA-256](artifacts/20261119T093631Z-preview/SHA256SUMS) · [Source archive](artifacts/kernova-os-0.1.2-source.tar.gz) · [Build and verification status](STATUS.md)

Почни со [упатството на македонски](START_HERE_MK.md). The detailed results are in [STATUS.md](STATUS.md) and the [verification matrix](docs/verification.md).

[Ажурирања преку Discover за постојните инсталации](docs/github-updates-mk.md)

## First build

Extract the supplied source archive onto ext4 in a dedicated Debian 13 amd64 VM. As your ordinary build account, install the builder dependencies, check the environment, run the source tests and build the foundation image.

```sh
cd ~/kernova-os
sudo ./scripts/install-prerequisites
./scripts/preflight
./scripts/check-source
./scripts/build-iso foundation
```

Boot the foundation image in a new VM. After Plasma starts, build the branded system with `./scripts/build-iso preview`. Each successful run prints the path to its own ISO and publishes the checksum, package manifest and build evidence together. The release filename for 0.1.2 is `kernova-os-0.1.2-amd64.iso`.

| Task | Entry point |
| --- | --- |
| Prepare Windows and Debian, verify the Debian download, build packages or ISO | [Build guide](docs/build.md) |
| Boot a new test disk and install interactively | [Installation and firmware tests](docs/install.md) |
| Change name, colors, wallpaper, applications or locale | [Architecture and customization](docs/architecture.md) |
| Update, recover, or prepare a release | [Maintenance and distribution](docs/maintenance.md) |
| Review test evidence and pending work | [Verification matrix](docs/verification.md) |

`auto/` and `config/` control live-build. `packages/` contains Debian source packaging, `apps/` the native application and `branding/` the editable artwork. `build/` is created for work trees, logs and virtual disks. `artifacts/` holds published local outputs. Keep prior successful builds for comparison.
