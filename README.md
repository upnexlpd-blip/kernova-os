# KERNOVA OS

KERNOVA OS is a Debian 13 desktop for 64-bit Intel and AMD computers. It includes KDE Plasma, Discover, a graphical installer, hardware settings and the KERNOVA Welcome app.

**Already running 0.1.2?** Connect the signed update channel once, open Discover and select **Update All** to upgrade to 0.1.3. New 0.1.3 installations include the channel. [Update instructions](docs/github-updates.md) · [Verified upgrade](docs/evidence/updates/discover-0.1.3.png)

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

Boot the foundation image in a new VM. After Plasma starts, build the branded system with `./scripts/build-iso preview`. Each successful run prints the path to its own ISO and publishes the checksum, package manifest and build evidence together. The release filename for 0.1.3 is `kernova-os-0.1.3-amd64.iso`.

| Task | Entry point |
| --- | --- |
| Prepare Windows and Debian, verify the Debian download, build packages or ISO | [Build guide](docs/build.md) |
| Boot a new test disk and install interactively | [Installation and firmware tests](docs/install.md) |
| Change name, colors, wallpaper, applications or locale | [Architecture and customization](docs/architecture.md) |
| Update, recover, or prepare a release | [Maintenance and distribution](docs/maintenance.md) |
| Review test evidence and pending work | [Verification matrix](docs/verification.md) |

`auto/` and `config/` control live-build. `packages/` contains Debian source packaging, `apps/` the native application and `branding/` the editable artwork. `build/` is created for work trees, logs and virtual disks. `artifacts/` holds published local outputs. Keep prior successful builds for comparison.
