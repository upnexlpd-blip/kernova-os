# KERNOVA OS

KERNOVA OS is a Debian 13 desktop for 64-bit Intel and AMD computers. It includes KDE Plasma, Discover, a graphical installer, hardware settings and the KERNOVA Welcome app.

**Download the full KERNOVA OS 0.1.8 USB image.** [Download the amd64 ISO](https://github.com/upnexlpd-blip/kernova-os/releases/download/v0.1.8/kernova-os-0.1.8-amd64.iso) · [Release notes and SHA-256 checksum](https://github.com/upnexlpd-blip/kernova-os/releases/tag/v0.1.8)

Write the image to a spare USB drive of 4 GB or larger in disk-image mode. Writing the image erases the selected USB drive. Boot the USB to try Plasma. Open **Install KERNOVA OS** on the Live desktop when you are ready to install.

**Already running KERNOVA 0.1.3 or later?** Open **Discover > Updates > Refresh > Update All** to upgrade the installed desktop. Existing 0.1.2 installations need the [one-time channel setup](docs/github-updates.md).

Start with the [quick start guide](START_HERE.md). See the [project status](STATUS.md) and [verification matrix](docs/verification.md) for release evidence.

## First build

Extract the supplied source archive onto ext4 in a dedicated Debian 13 amd64 VM. As your ordinary build account, install the builder dependencies, check the environment, run the source tests and build the foundation image.

```sh
cd ~/kernova-os
sudo ./scripts/install-prerequisites
./scripts/preflight
./scripts/check-source
./scripts/build-iso foundation
```

Boot the foundation image in a new VM. After Plasma starts, build the branded system with `./scripts/build-iso preview`. Each successful run prints the path to its own ISO and publishes the checksum, package manifest and build evidence together. For 0.1.8, the release filename is `kernova-os-0.1.8-amd64.iso`. To reproduce the release package selection, pass `--package-dir` followed by the directory containing the five published 0.1.8 Debian packages. The builder checks each package against the release manifest.

| Task | Entry point |
| --- | --- |
| Prepare Windows and Debian, verify the Debian download, build packages or ISO | [Build guide](docs/build.md) |
| Boot a new test disk and install interactively | [Installation and firmware tests](docs/install.md) |
| Change name, colors, wallpaper, applications or locale | [Architecture and customization](docs/architecture.md) |
| Update, recover, or prepare a release | [Maintenance and distribution](docs/maintenance.md) |
| Review test evidence and pending work | [Verification matrix](docs/verification.md) |

`auto/` and `config/` control live-build. `packages/` contains Debian source packaging, `apps/` the native application and `branding/` the editable artwork. `build/` is created for work trees, logs and virtual disks. `artifacts/` holds published local outputs. Keep prior successful builds for comparison.
