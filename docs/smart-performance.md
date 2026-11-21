# Smart Performance 0.1.4 testing release

For battery-triggered temporary holds and local pressure reports in the 0.1.18 candidate, see the [Adaptive Engine guide](adaptive-engine.md).

Smart Performance 0.1.4 has been approved for the standard stable channel. Installed 0.1.3 users can follow the [stable update instructions](github-updates.md). The following procedure records the earlier opt-in test.

## Install on an existing KERNOVA 0.1.3 testing desktop

Sign into the installed system and open Konsole. At the time of the test, stable users received 0.1.3 from the signed `apt` branch of `upnexlpd-blip/kernova-linux`. This opt-in adds the separate `apt-testing` branch of `upnexlpd-blip/kernova-os` alongside that source. Both use HTTPS. The testing key is scoped to its own deb822 source. The test was performed on an installed Debian 13 amd64 system using KDE Plasma, Discover, PackageKit, APT and dpkg.

Verify the source-file digest below against a copy received from your release operator before enrolling. The testing key fingerprint is `A009 D55D F827 E047 59C2 F263 7FB7 AAA2 9B49 472F`. APT subsequently verifies each signed index and the package digests it authenticates.

```sh
(
  set -eu
  f=$(mktemp)
  trap 'rm -f "$f"' EXIT
  curl -fsSL https://raw.githubusercontent.com/upnexlpd-blip/kernova-os/c3d4779d4bb5dedfb9c82dd4972244337df229e8/docs/testing.sources -o "$f"
  echo "023f0d3beabc1e2daf0e5dbb3bb34d49b294ef3745ef82c156f1154b8f7a8690  $f" | sha256sum -c -
  sudo install -m 0644 "$f" /etc/apt/sources.list.d/kernova-testing.sources
  sudo apt-get update --error-on=any
  apt-cache policy kernova-desktop
)
```

Expect installed 0.1.3 and candidate 0.1.4. Click the Plasma update notification or open **Discover Ã¢â€ â€™ Updates Ã¢â€ â€™ Refresh**. Select **Update All** and authenticate with your installed account. Discover downloads the packages, reports progress and refreshes the list on completion. Retry a failed transfer with **Refresh Ã¢â€ â€™ Update All** after restoring connectivity. Opening the application menu and searching **KERNOVA Performance Center** launches the new feature. **KERNOVA Update Center** shows installed and candidate versions, APT history and a restart message when the system provides `/run/reboot-required`.

```sh
dpkg-query -W kernova-desktop kernova-performance
kernova-performance-run coding -- make -j2
```

The second command is an example to run inside a build directory containing a Makefile. You can also enter a program and its arguments in the Performance Center. Each policy affects the launched workload and its descendants. Single-instance programs that forward work to an existing process can exit immediately. Use a fresh process for profiling.

| Profile | Linux scheduling changes | Optional hardware hold |
| --- | --- | --- |
| Gaming Mode | 10 Ã‚Âµs timer slack, inherited priority | Performance |
| Coding Mode | Batch policy, nice increment 3, 100 Ã‚Âµs timer slack | None |
| Battery Saver | Batch policy, nice increment 8, 10 ms timer slack | Power saver |
| Maximum Performance | 1 ns timer slack, inherited priority | Performance |

Supported power profiles are enumerated through `powerprofilesctl`. A requested hold lasts for the lifetime of the launched command. Software scheduling works without a hardware power provider. Exit the workload to end its profile. No configuration in sysfs or persistent privileged service is required. The GUI saves its preferred profile with per-user Qt settings.

## Roll back the testing release

Close profiled workloads after saving your work. When the stable index still offered 0.1.3, these commands restored all four original stable packages and removed the new package in the same APT transaction. Only use the procedure if every required version is still available from a trusted archive. They are specific to rolling 0.1.4 back to 0.1.3. Check that the stable source offers 0.1.3, then review the transaction before confirming.

```sh
sudo mv /etc/apt/sources.list.d/kernova-testing.sources /etc/apt/sources.list.d/kernova-testing.sources.disabled
sudo apt-get update --error-on=any
apt-cache policy kernova-desktop
sudo apt-get --allow-downgrades install kernova-desktop=0.1.3 kernova-welcome=0.1.3 kernova-default-settings=0.1.3 kernova-branding=0.1.3 kernova-performance-
dpkg-query -W kernova-desktop
```

If a transaction was interrupted after unpacking, run `sudo dpkg --configure -a`, then `sudo apt-get -f install` and review the proposed changes. Retry in Discover or use the rollback procedure after dpkg is consistent.

## Build and publish testing packages

The release source is on `dev/smart-performance-0.1.4`. The native source builds five architecture-independent Debian packages. The upgraded Welcome package pulls in the matching Smart Performance package. Its launchers, Python programs and dependency declarations live in `apps/performance`, `apps/integration` and `packages/debian`. The existing Discover notifier handles update checks and notifications.

1. On a Debian 13 build host, follow `docs/build.md` for the build dependencies, then run `python3 scripts/check-source` and `python3 scripts/build-packages artifacts/debs` as an ordinary user.
2. In GitHub **Settings Ã¢â€ â€™ Environments**, create the `testing` environment and restrict deployment to the exact development branch. Store only the dedicated testing private signing key in its environment secret `TESTING_SIGNING_KEY`. The workflow imports it in a temporary GnuPG home. For a new channel, generate a dedicated signing key offline with `gpg --quick-gen-key 'KERNOVA Testing Archive' ed25519 sign 1y`, export its public key, embed it in the deb822 source, register the matching fingerprint in the testing workflow and distribute that fingerprint independently. Keep the private key out of the checkout and terminal logs.
3. Enable GitHub Actions and allow the testing publisher's job token to write to this repository. Push the development branch with the new version in `product.json` and `packages/debian/changelog`. [Testing workflow](../.github/workflows/smart-performance-testing.yml)
4. The build job runs the source suite, resolves dependencies for all five packages, installs the feature in a disposable Debian container, runs it, interrupts and recovers package configuration, and tests removal. The publisher receives the tested files, signs and verifies the testing APT repository and SHA-256 manifest, pushes the archive branch and creates a GitHub prerelease.
5. The testing APT metadata expires after 14 days. To extend this particular release, rerun the verified renewal workflow from its Actions page before expiry. Renewal reuses the existing package bytes. Use a new version when changing the payload. The stable publisher has its own repository, source, key and release process. No VPS is used.

## Observed results

On 19 November 2026 the existing 0.1.3 UEFI test installation received **Updates available** after enrolling and refreshing APT. Discover offered four upgrades plus the new package. Clicking **Update All** installed 0.1.4 through PackageKit. A test document, KDE settings, machine identity, root filesystem UUID and the Firefox and Dolphin binaries were checked before and after. All four profiles produced distinct measured process settings. The GUI launched a command. A deliberately unreachable download endpoint left 0.1.3 intact. The same installed machine rolled back to 0.1.3 and subsequently accepted the update again. Physical battery life, frame rates and firmware power profiles were outside this VM test. An optional diagnostic invocation of `pkcon` was unavailable on the base image; APT and the running Discover notifier performed detection.

[Baseline](evidence/performance/before.png) Ã‚Â· [Native notification](evidence/performance/notification.png) Ã‚Â· [Discover candidates](evidence/performance/discover-candidate.png) Ã‚Â· [Failed download](evidence/performance/failed-download.png) Ã‚Â· [Completed update](evidence/performance/discover-complete.png) Ã‚Â· [APT history](evidence/performance/transaction.png) Ã‚Â· [Profile measurements](evidence/performance/installed-profiles.png) Ã‚Â· [Performance Center](evidence/performance/performance-center.png) Ã‚Â· [Rollback](evidence/performance/rollback.png) Ã‚Â· [GitHub Actions run](https://github.com/upnexlpd-blip/kernova-os/actions/runs/44550402625) Ã‚Â· [Release binaries and signed manifest](https://github.com/upnexlpd-blip/kernova-os/releases/tag/testing-v0.1.4)

The test guest also rejected a modified copy of the published testing InRelease with the installed APT verifier. The Debian CI suite exercised a bad signature independently, and the package installation test killed a dpkg process between unpacking and configuration, then recovered with dpkg. [Signature failure](evidence/performance/invalid-signature.png) Â· [CI tests and signed renewal](https://github.com/upnexlpd-blip/kernova-os/actions/runs/44551894088)

During an additional warm-restart check the Windows WHPX backend paused the virtual CPU with an unexpected exit. Starting the same installed disk in a fresh QEMU process succeeded. After signing in, all four profile checks and all file and identity checks passed again. [Installed disk after cold boot](evidence/performance/disk-boot.png)
