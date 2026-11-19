# Test on a new virtual disk

Use the graphical Debian builder or a separate Debian 13 test machine with the VM prerequisites installed. A nested guest can use KVM when the outer hypervisor exposes the CPU extensions and the account can access /dev/kvm. Otherwise the launcher selects QEMU software emulation and prints `tcg`. Expect slower boot, installation and graphics.

## Live and installation media

Set the `iso` variable to the validated **preview** from docs/build.md. Create the guest just once. Its private storage lives under `build/vms/uefi-one`. An existing name causes an error. The 40 GiB raw file is sparse on ext4 and uses more host space as the guest writes data. QEMU exposes only that writable disk and a read-only ISO, with user-mode networking and no port forwarding.

```sh
./scripts/vm create uefi-one --firmware uefi
./scripts/vm media uefi-one "$iso"
```

Choose **Live system (amd64)**. Try the [desktop checks](verification.md). The temporary `kernova-live` account is configured for automatic login with Debian live-config. Its upstream live password is `live`; the recipe requests `noroot` and an explicit group list. Test lock and unlock with this account. Live changes disappear at shutdown.

In the Calamares preview, open **Install KERNOVA OS** from the desktop or Plasma menu. The language selection page opens directly. Choose language, region and keyboard. On **Partitions** select the destination by model and capacity. On a second run, cancel at the summary and check the guest disk is unchanged before testing the actual install.

For the baseline choose **Erase disk** on the new **guest** disk. Verify it is the 40 GiB VirtIO device (about 42.9 GB in decimal, `/dev/vda`, serial `KERNOVA-TEST`). Enter a personal username such as `previewtester` and your own password. Review **Summary**, including the disk, filesystems and EFI system partition where applicable. Choose **Install** and confirm the final prompt. Calamares copies the ISO’s clean SquashFS, configures the new account and bootloader, and removes the live installer packages. At the reboot boundary power down after writes finish.

The GRUB **Start installer** entry remains available on both image profiles. It starts the Debian graphical installer and has its own account and disk workflow. For its baseline use guided partitioning of the new guest disk and ext4. The advanced GRUB menu includes text installer and rescue choices.

Start the installed guest without a virtual DVD. A successful login and second boot through this command are required for installation evidence.

```sh
./scripts/vm boot uefi-one
```

Log in as the new account. In Konsole, create a file, record its digest, choose a different Plasma color scheme and switch off Welcome at login. Refresh APT, then run the guest checker as your ordinary user.

```sh
mkdir -p ~/kernova-evidence
printf '%s\n' 'KERNOVA persistent file' > ~/kernova-evidence/persistent.txt
(cd ~/kernova-evidence && sha256sum persistent.txt > persistent.sha256)
sudo apt update
/usr/share/kernova/diagnostics/check-session installed --firmware uefi > ~/kernova-evidence/installed.json
```

Review the [account and authentication checks](verification.md) before accepting the installation. Restart, check the file with `(cd ~/kernova-evidence && sha256sum -c persistent.sha256)`, then follow the [update test](maintenance.md).

## BIOS and Secure Boot

Repeat the whole sequence on **separate new disks** named `bios-one` and `secure-one`. Change the firmware argument in the guest checker to match the guest. Use the same validated ISO for a comparison.

```sh
./scripts/vm create bios-one --firmware bios
./scripts/vm media bios-one "$iso"
# After completing the installer and powering down:
./scripts/vm boot bios-one

./scripts/vm create secure-one --firmware secure
./scripts/vm media secure-one "$iso"
# After completing the installer and powering down:
./scripts/vm boot secure-one
```

The launcher reads OVMF descriptors from the installed Debian package, gives each EFI guest its own variable store, and selects enrolled keys plus SMM for Secure Boot. Check both the live and installed sessions. SecureBoot must be 1 and SetupMode 0 in the running guest. Record the full output, kernel version, firmware package version and ISO digest. A signed executable in an ISO is only an image-content check. [Debian OVMF package contents](https://packages.debian.org/trixie/all/ovmf/filelist) and [trixie QEMU documentation](https://manpages.debian.org/trixie/qemu-system-x86/qemu-system-x86_64.1.en.html)

## Windows alongside test

Use a disposable copy of a licensed Windows guest in its original firmware mode. Keep the original virtual disk and recovery key separately. Record the partition map, EFI entries and a test file checksum in Windows first. Test the following layouts on separate copies.

- **Resizable NTFS**. With Windows fully shut down, Fast Startup disabled and an eligible unencrypted volume with sufficient free space, select the disk and **Install alongside**. Choose the intended partition and compare the before/after diagrams. The existing Windows system must retain room for its files and updates. Continue through the summary and confirmation. Calamares derives eligibility from the filesystem and available space. [Calamares partition options](https://calamares.io/docs/partitions/)
- **Unallocated space**. Prepare space using Windows Disk Management as needed. In **Manual partitioning**, create the ext4 root partition only within the unallocated range. For UEFI, assign the existing FAT EFI System Partition to `/boot/efi` and leave formatting disabled for it. Keep the Microsoft Reserved, Windows and recovery partitions intact. Review the new Linux partition, mounted ESP and intended format operations before confirming. [Windows shrink procedure](https://learn.microsoft.com/windows-server/storage/disk-management/shrink-a-basic-volume)
- **BitLocker, hibernation or insufficient space**. Keep the protected volume intact. If the proposed layout is unsuitable, cancel. Use space already freed by Windows or a separate target disk. Have the BitLocker recovery key available before firmware or boot configuration changes. [Microsoft recovery-key guidance](https://support.microsoft.com/en-us/windows/security/encryption/back-up-your-bitlocker-recovery-key)

Detach the ISO. Start KERNOVA, log in with the new account and complete the checks above. Start Windows Boot Manager from GRUB if present, then from the original firmware entry. Verify the test file hash, Windows recovery partition and original EFI/Microsoft files. A Windows boot and data check is required before marking dual boot passed. A Linux guest with an NTFS filesystem only exercises partition handling.
