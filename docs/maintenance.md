# Updates, recovery and release

## Installed guest update test

Use an installation that already booted from its own disk. Save user data to another location and record the initial package list, running kernel and package sources. Verify that trixie, trixie-updates and trixie-security resolve to Debian archives and that no source stanza uses trusted=yes or Trusted: yes. Inspect /etc/apt/sources.list and active .list/.sources files in /etc/apt/sources.list.d.

```sh
mkdir -p ~/kernova-evidence
dpkg-query -W > ~/kernova-evidence/before.packages
uname -r > ~/kernova-evidence/before.kernel
apt-cache policy > ~/kernova-evidence/before.policy
sudo apt update --error-on=any
apt list --upgradable
sudo apt upgrade
```

Review the proposed package changes. If the system is current, record a successful refresh and mark a **package-changing update** pending until an update is available. Discover is an alternative frontend for the same system packages. Record the APT history. Restart from Plasma, with the ISO detached, and repeat the correct firmware and account checks. In Konsole, confirm the test file and settings survive.

```sh
(cd ~/kernova-evidence && sha256sum -c persistent.sha256)
dpkg-query -W > ~/kernova-evidence/after.packages
uname -r > ~/kernova-evidence/after.kernel
diff -u ~/kernova-evidence/before.packages ~/kernova-evidence/after.packages
/usr/share/kernova/diagnostics/check-session installed --firmware uefi > ~/kernova-evidence/updated.json
```

Use the matching bios or secure argument for those guests. Keep the diff even when it exits 1 for expected changed packages.

## Local KERNOVA package updates

Update product.json and packages/debian/changelog together. Build **all five** packages as an ordinary user with `./scripts/build-packages build/updated-debs` in the builder. Transfer just those .deb files and their hashes to an empty folder in the installed test guest. Compare the transferred hashes. From that folder review and apply the local update using normal APT.

```sh
apt --simulate install ./kernova-*.deb
sudo apt install ./kernova-*.deb
dpkg-query -W 'kernova-*'
```

Use `./scripts/test-packages` in the dedicated builder for a disposable mmdebstrap lifecycle test. It builds a lower test version, installs it into a fresh trixie root, changes user preferences and a conffile, upgrades and exercises removal/purge. It checks package ownership, an unaffected existing home and continued desktop dependencies. It requires working unprivileged user namespaces with UID/GID ranges. If the host blocks this, run it on a suitable dedicated builder, and record the actual failure. Run a separate real desktop reboot test after updating the guest.

For VPS delivery, the release operator builds a signed repository snapshot and the client administrator enrolls the verified public key through a scoped APT source. Discover then reports available system upgrades in Plasma. The preview ships the enrollment tool and daily metadata-refresh setting. Activation requires a real HTTPS repository and an independently verified key fingerprint. [VPS release and enrollment instructions](vps-updates.md)

## Recovery

- **Graphics failure.** Use the failsafe entry on the live menu, or edit an installed GRUB entry for a one-time diagnostic boot with `nomodeset`. Use a TTY if the graphical session is unusable. Inspect `journalctl -b -u sddm`, `journalctl -b -k` and `systemctl --failed`. Record the graphics device and session type before changing a driver.
- **Kernel regression.** In the installed GRUB advanced options, choose an older installed kernel if available. Verify the kernel with `uname -r`. Keep a working kernel while diagnosing the update.
- **APT interruption.** Ensure the previous APT/dpkg operation has stopped. Inspect `dpkg --audit`, /var/log/apt/history.log and /var/log/dpkg.log. On the installed guest, complete interrupted configuration with `sudo dpkg --configure -a` and inspect `sudo apt --fix-broken install` before approving its proposed changes.
- **Disk boot failure.** Power off the guest and back up its private disk and EFI variable store together. Boot the ISO's installer advanced rescue mode. Use `lsblk -f` to identify the guest partition and filesystem. In the rescue shell, mount the identified filesystem read-only to recover user files to a separate backup destination. For ext4 forensic recovery use `ro,noload` to avoid journal replay. Unlock encrypted guest data with its owner’s passphrase when applicable. Keep device names specific to the observed guest. Restore a known-good powered-off virtual disk/NVRAM backup or reinstall to a fresh test disk and restore the user backup.
- **Recovery drill.** Save a file and its checksum outside the guest. Restore it to a new location, verify the checksum and open it in its normal application. Record which backup, firmware mode, kernel and artifact actually worked.

The baseline uses conventional ext4 and APT. Rollback is a backup-and-restore operation. Previous release directories retain the matching manifests, configuration and hashes for investigating changes.

## Publishing and licensing

The recipe tracks the trixie suite, its updates and security archive. Package versions change as the archives advance. Save the exact manifest and logs of each build. A bit-identical release would also require frozen authenticated repository snapshots, controlled toolchain and timestamps, and a matching independent rebuild. Choose the refresh schedule for security fixes separately.

KERNOVA's original code and artwork use the root MIT LICENSE. Debian packages, KDE assets, fonts and firmware retain their own licenses, notices and trademarks. Before distributing an ISO, inventory the **actual** manifest, retain the corresponding source versions and build scripts for applicable copyleft binaries, review each copyright file and firmware redistribution terms, and select a source delivery method permitted by each license. Collect /usr/share/doc/*/copyright from the image, including symlink targets. Document modifications and preserve notices. Verify trademark presentation and applicable firmware restrictions for the planned distribution. Do not treat the KERNOVA license as a relicensing of the image. [Debian copyright information](https://www.debian.org/doc/debian-policy/ch-docs.html#copyright-information)

A development preview can be promoted only after the required live, installed and post-update checks have evidence for the advertised boot profiles. Keep physical hardware support specific to tested devices.
