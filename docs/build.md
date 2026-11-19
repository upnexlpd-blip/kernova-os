# Build on a dedicated Debian machine

## Windows host

This workspace now has a dedicated Debian 13 console VM on D: and a portable QEMU for Windows. For access to that existing builder and its progress log, use the [local guide in Macedonian](windows-builder-mk.md). The following setup procedure also applies to a fresh machine.

Windows can edit, test portable source, and transfer this project. The privileged stages need a Linux kernel with private mounts, device creation and chroot. This workspace is on NTFS. The host has 12 logical CPUs and about 32 GiB RAM. At the initial check it had about 46 GiB free on C: and 675 GiB free on D:. Windows reported that hardware virtualization was disabled in firmware. The local QEMU builder uses software emulation and its own ext4 filesystem.

Use a Debian 13 amd64 machine or VM you control. For a new VM in your chosen Windows hypervisor, create a new virtual machine with a new, dynamically allocated disk and NAT networking. Start with 4 vCPUs, 8 GiB RAM and 80 GB for one build. Allow more storage (for example 140 GB) if retaining foundation and preview work trees and several installed test guests. Allocate space on a volume with room for the disk to grow. These are development allocations. A hardware-accelerated hypervisor needs virtualization support enabled by the owner. A software-emulated x86 VM can run without it, at a considerable speed cost. An existing Debian machine is another route.

Download the **amd64 netinst** for Debian **13 trixie**, its SHA512SUMS and SHA512SUMS.sign from the same official directory. Debian 13.7 was the listed point release during this handoff. [Debian 13 installation media](https://www.debian.org/releases/trixie/debian-installer/)

Verify the signature on the checksum file using a Debian CD signing key. On a trusted Debian system with `debian-keyring` installed, use the following commands in a folder containing the downloaded ISO and both checksum files. Check that the exact ISO filename reports OK.

```sh
gpgv --keyring /usr/share/keyrings/debian-role-keys.pgp SHA512SUMS.sign SHA512SUMS
sha512sum --check --ignore-missing SHA512SUMS
```

On Windows with Git Bash, obtain the **public** signing key from Debian's verification page and compare the full primary fingerprint with that page through a trusted channel. Save the key as `debian-cd-key.asc`. From the download folder, use an isolated keyring for this verification and check the ISO hash against the authenticated list. A good signature from an unknown signer does not establish provenance. [Debian image verification and CD key fingerprints](https://www.debian.org/CD/verify)

```sh
mkdir -m 700 cd-keyring
gpg --homedir ./cd-keyring --show-keys --fingerprint debian-cd-key.asc
gpg --homedir ./cd-keyring --import debian-cd-key.asc
gpg --homedir ./cd-keyring --verify SHA512SUMS.sign SHA512SUMS
sha512sum --check --ignore-missing SHA512SUMS
```

Attach the verified ISO as a virtual DVD, install Debian onto the **builder's new virtual disk**, and select a graphical desktop and standard system utilities. Set up a normal account with sudo. A blank root password in Debian Installer generally assigns administrative rights to the first user. A graphical session with PipeWire-Pulse or PulseAudio allows the QEMU test window and audio checks. Detach the Debian DVD after installation. [Debian amd64 installation guide](https://www.debian.org/releases/trixie/amd64/index.en.html)

## Debian build VM

Transfer `kernova-os-0.1.0-source.tar.gz` and its `.sha256` file to the builder's Downloads folder using your VM manager's file transfer, a read-only share, or separate virtual data media. The supplied tar archive preserves Linux permissions. Verify it and extract once into your **own home directory on ext4**. The checksum identifies this local transfer. Debian's archive keyring authenticates upstream packages during the build.

```sh
cd ~/Downloads
sha256sum -c kernova-os-0.1.0-source.tar.gz.sha256
test ! -e ~/kernova-os && tar -xzf kernova-os-0.1.0-source.tar.gz -C ~
cd ~/kernova-os
```

Check the builder once before installing prerequisites. With missing tools the preflight exits nonzero and lists them. Install the prerequisites **inside this Debian VM**, then run preflight again for a full result. It checks the installed live-build version, repository access, Linux filesystem and a temporary private mount, chroot and device node.

```sh
./scripts/preflight
sudo ./scripts/install-prerequisites
./scripts/preflight
./scripts/check-source
```

To build only the local Debian packages, run the following as the ordinary build account. Use a fresh output directory for another run. Full source archives, .changes, .buildinfo and the package build log remain in the job directory printed by the builder.

```sh
./scripts/build-packages build/debs-0.1.0
```

For the first image, use the foundation profile. It includes the live KDE session and interactive installer. After checking that it boots, build the complete preview. Each invocation creates a fresh work directory and uses sudo for isolated privileged operations.

```sh
./scripts/build-iso foundation
# After the foundation desktop boot check in docs/install.md:
./scripts/build-iso preview
```

Follow the printed output path. In Bash, choose the actual successful preview directory, then independently recheck its ISO and open the build records. With multiple builds, deliberately select the one you intend to test.

```sh
ls -d artifacts/*-preview
read -r -p 'Preview output directory: ' release
iso="$release/kernova-os-0.1.0-amd64.iso"
./scripts/validate-iso "$iso"
less "$release/build.log"
```

For a failed build, read `build/<run>/build.log` starting at the first failing stage. For a package failure, also read its reported `build/packages-*/build.log`. Fix the input or builder problem and rerun the same entry point. Failed work and previously published builds stay available for diagnosis. Files inside chroots remain root-owned. Inspect retained mounts with `findmnt` before reclaiming a work tree. Reverting a disposable build-VM snapshot is a simple way to reclaim space after saving evidence and any desired artifacts.

For another source handoff from a committed local checkout, use Git's archive support so executable bits and revision metadata survive Windows. From the repository root in Git Bash, run:

```sh
git archive --format=tar.gz --prefix=kernova-os/ -o artifacts/kernova-os-0.1.0-source.tar.gz HEAD
(cd artifacts && sha256sum kernova-os-0.1.0-source.tar.gz > kernova-os-0.1.0-source.tar.gz.sha256)
```
