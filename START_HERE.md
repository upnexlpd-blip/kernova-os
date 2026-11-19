# Getting started with KERNOVA OS

KERNOVA is a Debian 13 desktop for 64-bit Intel and AMD computers. If you already have 0.1.2 installed, you can upgrade in place. [Set up Discover updates](docs/github-updates.md)

## Try the desktop

Boot the USB and select **Live system (amd64)**. Open **App Download** in the application menu to use Discover. KERNOVA Welcome offers Chrome, Viber, Telegram and ZapZap. Save files you want to keep before ending the Live session. [Desktop guide](docs/user-guide.md)

## Install

Open **Install KERNOVA OS**. From 0.1.2 onward the local Live user can open the installer directly. The older 0.1.1 desktop launcher asks for the temporary password `live`. The Foundation image offers **Start installer** in the boot menu.

1. Choose your language, time zone and keyboard.
2. Identify the destination disk by its model and capacity. **Erase disk** replaces its partitions. On an eligible Windows installation, **Install alongside** can resize an existing partition. Back up the machine, save the BitLocker recovery key, disable Fast Startup and fully shut down Windows before resizing NTFS.
3. For existing unallocated space, use manual partitioning and create an ext4 root partition within that space. In UEFI mode mount the existing EFI System Partition at `/boot/efi` with formatting disabled. Preserve the Windows and recovery partitions.
4. Choose your personal username and password on **Users**. Check the proposed disk operations on **Summary** before confirming. After installation, remove the USB and sign in. See the installation guide for VM test procedures and the current limits of dual-boot testing. [Installation guide](docs/install.md)

## Build from source

Use a dedicated Debian 13 amd64 builder with ext4. The local test configuration uses four vCPUs, 8 GiB RAM and an 80 GiB dynamically allocated disk. Verify the Debian installation image against its signed SHA-512 manifest. [Build guide](docs/build.md)

```sh
git clone https://github.com/upnexlpd-blip/kernova-os.git
cd kernova-os
sudo ./scripts/install-prerequisites
./scripts/preflight
./scripts/check-source
./scripts/build-iso preview
```

Run the build as the ordinary builder account. For a minimal image use the foundation profile. Each successful run prints its ISO path and records its checksum, package manifest and build log. Use a new test disk for installation checks.

```sh
read -r -p 'ISO path: ' iso
./scripts/validate-iso "$iso"
./scripts/vm create uefi-one --firmware uefi
./scripts/vm media uefi-one "$iso"
```

See the [Windows builder notes](docs/windows-builder.md), [verification matrix](docs/verification.md) and [maintenance guide](docs/maintenance.md).
