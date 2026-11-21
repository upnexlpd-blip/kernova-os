# Adaptive Engine v1

Debian 13 amd64 and KDE Plasma use the existing `kernova-performance` package for workload scheduling and power-profile integration. The additional system service starts in observation mode. It does not require a network, account or desktop session. Continue to use Plasma's power controls for manual changes.

## Enable or inspect

```sh
kernova-adaptive status
kernova-adaptive status --json
sudo kernova-adaptive auto on
kernova-adaptive report --json
sudo kernova-adaptive auto off
```

Set integer `enter_threshold` and `exit_threshold` in `/etc/kernova/adaptive.json`. The lower value must be positive, smaller than the upper value, and the upper value at most 100. Configuration is reread on events and at least once per minute.

| State | Behavior |
| --- | --- |
| OBSERVE | Automation is off. |
| AUTO | At or below 20% on battery, request one temporary power-saver hold. Keep it in the middle band only if low battery was previously latched. Release at 25% or on confirmed AC. Yield to competing holds. |
| EXTERNAL_OVERRIDE | A different profile transition or an unexpected revocation was reported. This decision survives service and machine restarts. Explicitly enable to resume. |
| UNAVAILABLE | No reliable system battery, unsafe or unknown provider, denied authorization, conflicting controller or unusable configuration. Consult the reason in status. |

The interface is `org.freedesktop.UPower.PowerProfiles`. V1 verifies the bus owner's systemd unit, reported 0.30 series, available profiles and hold methods/signal. It only requests power-saver. PowerDevil and the Performance Center continue using the same provider. Active TLP, tuned, auto-cpufreq and system76-power units block automation. Alternative providers and unmanaged controllers outside these detectable units have not been qualified. PPD itself cannot report a manual selection that leaves its active profile unchanged.

The UPower display device must be a present battery. The fallback accepts one present battery marked as a system power supply. Unknown charge state, disagreement with OnBattery, samples over ten minutes old, future timestamps and pre-resume readings inhibit holds. Mouse and headset percentages do not drive policy. Background events are coalesced for 350 ms. Notifications of external decisions are processed immediately. A 60-second watchdog covers missed events and data expiry. Retry delays grow from one to 60 seconds.

The service uses a dedicated non-login system user and a private system-bus connection. Polkit grants this identity the hold action only. The hold cookie belongs to that connection and provider instance. A clean stop releases it and PPD removes requests when their connection disappears. The engine never writes a previous profile back. Debian retains the conffile and private automation state on removal and clears them on purge. Choose `auto off` to disable only the adaptive policy while keeping Performance Center.

The report includes kernel CPU, memory and I/O pressure from `/proc/pressure`. Average fields describe stall percentages over 10, 60 and 300 seconds, and total is microseconds. A missing resource is JSON null. Reports contain no device identifiers. Hardware temperature and estimated battery-life gains are outside v1.

## Candidate update

Install all five matching Debian packages together because Welcome and the branding packages have exact version dependencies. In a directory containing the verified candidate binaries, run:

```sh
sudo apt install --no-remove ./kernova-*_0.1.18_all.deb
systemctl status kernova-adaptive
```

The verify job builds and tests the source on Debian trixie. The existing release process signs testing metadata in its protected publishing environment. Deployment from testing requires the configured testing source and an actually published candidate. Stable promotion is a separate release decision.

Upstream references: [power-profiles-daemon hold lifecycle](https://upower.pages.freedesktop.org/power-profiles-daemon/gdbus-org.freedesktop.UPower.PowerProfiles.html), [UPower](https://upower.freedesktop.org/docs/), [Linux PSI](https://docs.kernel.org/accounting/psi.html).

See the [Debian guest results and idle measurements](evidence/adaptive-0.1.18.md).

The [0.1.19 installed-system validation](evidence/system-help-0.1.19.md) covers upgrading a persistent desktop, preserving manual override across reboot and installing System Help. For a system without the optional power-profiles-daemon provider, the engine reports UNAVAILABLE. The supported provider in these tests was Debian's 0.30 series. While the service is running, its refresh also checks for a changed effective profile when a transition signal was missed.
