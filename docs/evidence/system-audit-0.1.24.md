# Desktop performance and stability audit

Tested on 22 November 2026. The baseline was the stable desktop source at `d994d90` and an installed `0.1.23+stable1` UEFI guest. The candidate was built as `0.1.24` on Debian 13.7 amd64 and installed locally. The guest used QEMU/WHPX on Windows, four virtual CPUs, 4 GiB RAM, an ext4 system disk and KDE Plasma Wayland. Both versions used Linux `6.12.117+deb13-amd64`.

## Timings

Each row gives the median of seven repetitions after one warm-up in the same installed guest. The first three rows cover a complete helper invocation. The last two measure how long the Qt constructor or tab switch held the caller. The test waited for the package query to finish and checked its result after every switch.

| Operation | Stable | Candidate |
| --- | ---: | ---: |
| Plasma catalog hook for an initialized account | 40.14 ms | 0.76 ms |
| Torrent login check with a fresh state directory | 270.85 ms | 30.05 ms |
| Weather panel refresh with no saved location | 98.32 ms | 74.91 ms |
| Construct the Performance Center window | 121.34 ms | 28.03 ms |
| Open its System updates tab | 35.79 ms | 0.30 ms |

One cold boot per version reached the systemd graphical target. Kernel plus userspace took 7.637 s on stable and 7.314 s on the candidate. The component timings above provide the repeat measurements. Physical boot, firmware and usable-desktop times require separate measurements.

## Stability and regression checks

- With deliberately malformed saved settings, the stable Adaptive Engine restarted twice within 12 seconds. The candidate stayed active with zero restarts, kept the damaged file and reported the configuration error. An explicit `kernova-adaptive auto off` restored valid saved settings. Adapter tests also exercised incomplete D-Bus notifications, provider loss and retry timers.
- Periodic Torrent checkpoints now skip unchanged resume data and batch writes. In the upgraded guest, a loopback transfer closed with 128 of 512 pieces saved, reopened and finished. Both 8 MiB payloads had SHA-256 `8c47e14487ed495a3765d1eea4e414f3ba6ebefa832abddbff65ea7091c7f0d0`.
- The GUI tests exercised rapid chart selection in Crypto, closing the Welcome guide, delayed package queries and truncated APT history. The catalog login test covered a prepared account and retry after incomplete setup.
- Debian's `scripts/check-source` passed all 91 tests, ShellCheck and desktop-file validation. The Welcome suite passed all 13 cases again at 2× scale. Node passed all 6 Window Tools tests.
- APT upgraded all six packages. File verification, dependency checks and the hashes of the existing KWin settings and Debian identity file passed. After power-off and cold boot, KWin answered on D-Bus and both system and user sessions had zero failed units.
- The installed session diagnostic passed all 28 applicable assertions and detected Ethernet. System Help returned eight healthy checks including HTTPS, PipeWire, package state, disk space and kernel pressure. The battery check reported no battery in the guest.
- On a second installed test disk the package lifecycle fixture upgraded modified defaults and verified two user profiles, looked up the installed KDE theme, wallpaper and Window Tools, then removed and purged the cosmetic packages. The core desktop and existing user files survived.
- The complete `scripts/test-packages` run also passed from a fresh, minimal Debian 13 chroot. It installed the desktop, upgraded the synthetic `0.1.24~test1` packages and checked removal and purge. The builder reused cached Debian archives and fetched missing dependencies through APT. The test now stages the Window Tools guide, checks the wallpaper by its installed path and uses disk-backed temporary space by default.

## Coverage and evidence

The firmware test used UEFI with Secure Boot off. The VM exposed Ethernet and a virtual sound device. Physical battery transitions, Wi-Fi, Bluetooth transfers, GPU performance, suspend/resume and extended uptime require hardware testing. BlueZ logged two contacts-registry warnings because Evolution Data Server was absent. Its OBEX service was active and exposed its client interface, with zero restarts.

The local audit bundle is under `artifacts/system-audit-0.1.24/`. It contains the six Debian packages, their SHA-256 manifest, the benchmark probes and transcripts under `evidence/`. The public update channel was outside this local test.
