# Test on a new virtual disk

Use the graphical Debian builder or a separate Debian 13 test machine with the VM prerequisites installed. A nested guest can use KVM when the outer hypervisor exposes the CPU extensions and the account can access /dev/kvm. Otherwise the launcher selects QEMU software emulation and prints `tcg`. Expect slower boot, installation and graphics.

## Live and installation media

Set the `iso` variable to the validated **preview** from docs/build.md. Create the guest just once. Its private storage lives under `build/vms/uefi-one`. An existing name causes an error. The 40 GiB raw file is sparse on ext4 and uses more host space as the guest writes data. QEMU exposes only that writable disk and a read-only ISO, with user-mode networking and no port forwarding.

```sh
./scripts/vm create uefi-one --firmware uefi
./scripts/vm media uefi-one "$iso"
```

Choose **Live system (amd64)**. Try the [desktop checks](verification.md). The temporary `kernova-live` account is configured for automatic login with Debian live-config. Its upstream live password is `live`; the recipe requests `noroot` and an explicit group list. Test lock and unlock with this account. Live changes disappear at shutdown.

Shut down Plasma, reopen the same guest with the same media command, and choose **Start installer** from GRUB. The advanced menu also provides text installer and rescue choices. Select language, keyboard, timezone and your account. Choose a distinct personal username such as `previewtester`. Leave the root password blank if you intend to use Debian's first-user sudo setup. Supply your own password when prompted.

For the baseline, choose guided partitioning using the entire **guest** disk and ext4. Confirm that the only writable disk is the 40 GiB VirtIO device (about 42.9 GB in decimal, `/dev/vda`, serial `KERNOVA-TEST`). Review the proposed partition table, ESP in UEFI mode, and the final write confirmation. Direct the bootloader to that guest disk. Allow d-i to transfer the live filesystem and finish. At the reboot boundary close the guest once writes have finished or power it off when it returns to the ISO menu.

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

This validation is scoped to virtual disks. Physical installation, encryption testing and dual boot have separate targets and evidence requirements.
