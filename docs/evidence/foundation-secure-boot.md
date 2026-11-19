# Foundation 0.1.0 Live with enrolled Secure Boot

On 19 November 2026, the foundation ISO booted its default Live entry in two independent Windows-hosted QEMU guests. The first used a read-only virtual optical drive. The second presented the unmodified hybrid image as a read-only removable USB mass-storage device. Both reached the ordinary `kernova-live` shell and reported `SecureBoot=1`, `SetupMode=0` and kernel lockdown in integrity mode.

The tested ISO was `kernova-os-0.1.0-amd64.iso`, SHA-256 `52ab0d7191c4c730f3da23651272e5f23d8c660398ae75a64f8a33c54d46942b`. Both runs used QEMU 11.1.0, Q35 with SMM, protected pflash, TCG, two vCPUs and 2,304 MiB RAM. The project selector chose Debian OVMF `2025.02-8+deb13u1` and its `40-edk2-x86_64-secure-enrolled.json` descriptor with enrolled Microsoft keys. Each VM received fresh private variable storage. Its boot medium was the only guest disk device. Both guests powered off using `systemctl poweroff`. [Optical records](../../artifacts/20261118T231642Z-foundation/secure-boot-evidence/optical/) · [USB records](../../artifacts/20261118T231642Z-foundation/secure-boot-evidence/usb/)

| Observation | Optical | Removable USB |
| --- | --- | --- |
| Guest UUID | `e12272dd-1ee7-489c-bccb-468aa33f7dd5` | `0e611ec0-8dd9-4865-ac08-dce53d452322` |
| OVMF boot device | UEFI QEMU DVD-ROM | UEFI QEMU USB HARDDRIVE on the xHCI controller |
| Kernel EFI stub reported | UEFI Secure Boot is enabled | UEFI Secure Boot is enabled |
| Running kernel | `6.12.117+deb13-amd64` | `6.12.117+deb13-amd64` |
| Live medium | `/dev/sr0`, ISO 9660 | `/dev/sda`, ISO 9660, USB transport, RO=1, RM=1 |
| Guest SecureBoot / SetupMode | [1 / 0](../../artifacts/20261118T231642Z-foundation/secure-boot-evidence/optical/guest-efivars.png) | [1 / 0](../../artifacts/20261118T231642Z-foundation/secure-boot-evidence/usb/guest-efivars.png) |

The EFI system partition's `EFI/BOOT/BOOTX64.EFI` identified itself in SBAT as Debian shim 16.1. Its SHA-256 was `e103c5d02657879f141b086ed703584d28bb9e2721b423333be085ee1b4d397b`. `GRUBX64.EFI` identified itself as Debian GRUB `2.12-9+deb13u2`, SHA-256 `b102e12508c773796d102d58f81bb8a00357c01daa09092ae1d2b1d1702bc310`. Each firmware serial log recorded the device path and the kernel EFI stub loading the initrd. [Optical serial output](../../artifacts/20261118T231642Z-foundation/secure-boot-evidence/optical/serial.log) · [USB serial output](../../artifacts/20261118T231642Z-foundation/secure-boot-evidence/usb/serial.log)

The console probe read the byte immediately following the four efivarfs attribute bytes.

```sh
uname -r
findmnt -no SOURCE,FSTYPE /run/live/medium
cd /sys/firmware/efi/efivars
for name in SecureBoot SetupMode; do
    printf '%s ' "$name"
    od -An -tu1 -j4 -N1 "$name-8be4df61-93ca-11d2-aa0d-00e098032b8c"
done
cat /sys/kernel/security/lockdown
```

The USB guest also confirmed the Live filesystem at `/run/live/medium/live/filesystem.squashfs`. The compatibility path `/lib/live/mount/medium/live` was absent, and resolving `/lib/live/mount/medium` with `readlink -f` failed. [Guest filesystem check](../../artifacts/20261118T231642Z-foundation/secure-boot-evidence/usb/guest-media-paths.png)

This covers the foundation Live image on the specified emulated firmware. Physical firmware, installed-disk boot and other ISO revisions need their own checks.
