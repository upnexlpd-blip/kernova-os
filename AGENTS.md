# KERNOVA OS

Keep source work inside this project. Read STATUS.md and docs/verification.md before picking up a milestone. The project targets Debian trixie amd64.

- Keep product identity in product.json. Bump the Debian changelog with each package release. Preserve package ownership, existing home directories and Debian identity files across upgrades.
- Treat auto/ and config/ as inputs. Always generate live-build state in a fresh build directory. Keep generated media, tools, chroots and private test disks out of the source archive.
- Build Debian packages without root. Run privileged build steps only in a dedicated Debian builder. Do not expose physical disks, host credentials, remote management services or a host bootloader to the test VM.
- Use scripts/check-source for source validation and docs/verification.md for independent runtime checks. Record the exact version, platform, procedure, result and path to evidence before promoting a check to Passed.
- Preserve existing artifacts and failed logs. Keep firmware modes, live boot, disk boot, package lifecycle and post-update boot as separate evidence.
- Keep the standard installer interactive. Changes to package distribution, physical hardware or externally published resources require a separate decision.
