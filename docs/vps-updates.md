# Host a signed KERNOVA archive on a VPS

The default public channel is hosted on GitHub. These instructions describe a separate operator-managed HTTPS archive. [Default channel and enrollment](github-updates.md)

## Produce and publish a snapshot

Build all four matching Debian packages on Debian trixie. Each released version must be greater than its predecessor according to `dpkg --compare-versions`. Use a dedicated OpenPGP key. Store the primary private key, recovery copy and revocation certificate separately from the web server. Set VERSION and FINGERPRINT to the release version and verified full primary fingerprint.

```sh
./scripts/build-packages "artifacts/debs-$VERSION"
python3 scripts/build-update-repo "artifacts/debs-$VERSION" "artifacts/repo-$VERSION" "$FINGERPRINT"
```

The release helper checks package names, versions and architecture and verifies InRelease against the exported public key. Publish pool files first, keeping earlier package files accessible. Stage dists separately and switch the active indexes atomically. Serve kernova-archive-key.asc and dists/kernova-trixie/InRelease over HTTPS. Indexes expire after 14 days. Renew them weekly with the original .deb files.

## Enroll a client

Verify the full fingerprint independently. Set REPO_URL to the archive's HTTPS root and run the following in a fresh directory on the installed system.

```sh
set -e
curl --fail --show-error --location --proto '=https' --proto-redir '=https' \
    -o kernova-archive-key.asc "${REPO_URL%/}/kernova-archive-key.asc"
kernova-update-source "$REPO_URL" kernova-archive-key.asc "$FINGERPRINT" kernova.sources
sudo install -m 0644 kernova.sources /etc/apt/sources.list.d/kernova.sources
sudo apt-get update --error-on=any
apt-cache policy kernova-desktop kernova-welcome
```

The helper verifies the primary key fingerprint and embeds that key in the source's Signed-By field. An administrator can distribute the verified source through an existing trusted management channel.

## Verify delivery

On Debian, run `python3 -B -m unittest discover -s tests -p test_update_repo.py -v` as an ordinary user with reprepro, GnuPG and APT installed. The test creates a temporary key and verifies version selection and rejection of damaged signatures.

On a client, inspect `systemctl list-timers apt-daily.timer` and `apt-config dump`. Plasma starts DiscoverNotifier on sign-in. Notification intervals, power settings and Do Not Disturb affect when users see the alert. Compare the candidate version in Discover with apt-cache policy. After upgrading, verify the installed versions with `dpkg-query -W 'kernova-*'`.

Before rotating keys, distribute the new fingerprint over an independent trusted channel. In case of compromise, stop publication and disable the source until it can be verified again. [APT archive authentication](https://manpages.debian.org/trixie/apt/apt-secure.8.en.html) · [reprepro manual](https://manpages.debian.org/trixie/reprepro/reprepro.1.en.html)
