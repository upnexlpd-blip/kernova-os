# Installation reporting source verification

Verified on 19 November 2026 on Windows with Python 3.12 and the existing host-qt dependencies.

The source adds a manually opened installation reporting dialog to Welcome's System page. Consent starts unchecked. A report contains the OS version, an installed-session flag, a random registration ID and an authentication secret. Repeated submissions reuse the registration ID. Withdrawal uses the same service and secret. Live and unknown sessions are rejected before network access.

Ran scripts/check-source with PYTHONPATH=build/host-qt. Python compilation, shell syntax and ShellCheck passed. All 41 tests passed, with two environment-dependent checks skipped. Native Debian desktop-file validation and the newly packaged application on a booted Debian installation remain unverified. The source validation transcript is in the host temporary file kernova-admin-source-check.txt.

Added regression coverage for endpoint restrictions, Live/unknown rejection, stable retry credentials, payload fields and withdrawal. No report was sent from this host. The website server's separate seven integration tests passed against temporary databases. They cover sign-in, origin checks, session invalidation, download request counting, HEAD exclusion, data isolation, consent, deduplication, withdrawal and persistence.

No ISO or package release was created by this change. The service endpoint must be configured and the updated Welcome package distributed before existing users can participate. Reporting is voluntary and self-reported. It is not hardware attestation and cannot establish the total number of installed or active devices.
