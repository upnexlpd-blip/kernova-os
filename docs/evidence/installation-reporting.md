# Installation reporting source verification

Verified on 19 November 2026 on Windows with Python 3.12 and the existing host-qt dependencies.

The source adds a manually opened installation reporting dialog to Welcome's System page. Consent starts unchecked. A report contains the OS version, an installed-session flag, a random registration ID and an authentication secret. Repeated submissions reuse the registration ID. Withdrawal uses the same service and secret. Live and unknown sessions are rejected before network access.

Ran scripts/check-source with PYTHONPATH=build/host-qt. Python compilation, shell syntax and ShellCheck passed. All 41 tests passed, with two environment-dependent checks skipped. Native Debian desktop-file validation and the newly packaged application on a booted Debian installation remain unverified. The source validation transcript is in the host temporary file kernova-admin-source-check.txt.

Added regression coverage for endpoint restrictions, Live/unknown rejection, stable retry credentials, payload fields and withdrawal. No report was sent from this host. The website server's separate seven integration tests passed against temporary databases. They cover sign-in, origin checks, session invalidation, download request counting, HEAD exclusion, data isolation, consent, deduplication, withdrawal and persistence.

Version 0.1.8 was built and tested on Debian 13 by GitHub Actions run 44579595061, then published to the stable signed package channel by run 44579935031. Windows independently verified the archive signature using the previously embedded primary fingerprint 7656A706E55A3F68686DE0FDB9EF5C29B22041E8, the signed index hash, and all five published package hashes. The published Welcome package contains the reporting module, its Start/System entry points and /etc/kernova/statistics.json with the HTTPS endpoint.

The service is active at https://kernova-installations.upnexlpd.chatgpt.site. A production API test registered a temporary random ID, repeated the request, verified a single additional report and withdrew it. The count returned to zero. The local admin panel successfully reads the protected production aggregate.

Reporting is voluntary and self-reported. It cannot establish the total number of installed or active devices. The original ISO is unchanged. Existing installations require the 0.1.8 Welcome update through Discover, and their owners must choose to share a report. The first interactive report from a booted Debian installation remains unverified. Native source checks and packaged-file inspection cover the client integration.

CI validation https://github.com/upnexlpd-blip/kernova-os/actions/runs/44579595061

Stable publication https://github.com/upnexlpd-blip/kernova-os/actions/runs/44579935031

Local artifact verification build/installation-reporting/stable/verification.json in the primary checkout.
