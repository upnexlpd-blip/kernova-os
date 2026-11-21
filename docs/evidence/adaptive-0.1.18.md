# Adaptive Engine candidate validation · 21 November 2026

The isolated Debian 13 amd64 QEMU guest booted the KDE graphical target with WHPX, four virtual CPUs and 6 GiB RAM. It began with all five 0.1.17 packages installed. APT upgraded the running system to all five 0.1.18 binaries together with `--no-remove`. The candidate media transported Debian packages. The upgrade did not replace the guest's boot image. This run used a disposable Live filesystem overlay.

The service connected as the dedicated non-login user. The actual D-Bus owner resolved to power-profiles-daemon.service, exposing balanced, power-saver, HoldProfile, ReleaseProfile and ProfileReleased. UPower reported no present system battery. The production service reported UNAVAILABLE and emitted local PSI diagnostics. The guest probe supplied a synthetic charge reading to the installed policy while exercising the real daemon and system bus. It verified a single power-saver request, AC release, connection-loss cleanup as the service account and revocation by a separate D-Bus client. The guest also exercised CLI enable/disable, persistence of an external override across package reconfiguration, explicit re-enable, service stop/start, remove with configuration retained and purge with state removed. The harness reported `Adaptive lifecycle passed` and `QA-DONE`.

| Idle sample | Seconds | Service CPU (% of one CPU) | Service RSS | Guest CPU busy | Guest memory used |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0.1.17 baseline | 60.0 | 0 (service absent) | 0 | 0.359% | 1,694,260 KiB |
| 0.1.18 candidate | 60.0 | 0.050% | 29,128 KiB | 0.071% | 1,756,740 KiB |

The harness samples process ticks and VmRSS separately from aggregate guest CPU ticks and MemTotal minus MemAvailable. Guest totals include the desktop, background services and package activity. These single idle intervals do not estimate battery life.

The Debian CI check ran 67 tests, built the five native packages and exercised the package checks. The portable Windows source check completed with six platform-dependent skips. [Debian validation run](https://github.com/upnexlpd-blip/kernova-os/actions/runs/44928902286). The binaries used in the guest came from [the verified package build](https://github.com/upnexlpd-blip/kernova-os/actions/runs/44928300948). Only tests and CI dependencies changed between those builds.

Still to validate on a supported laptop: AC insertion/removal near both thresholds, UPower freshness across real lid suspend/resume, a physical power-supply battery, thermal throttling and firmware critical-battery handling. No physical energy or thermal measurements were made.
