# Your KERNOVA desktop

KERNOVA OS 0.1.0 development preview uses KDE Plasma on Debian 13. Open the application launcher with the Meta key. Search for KERNOVA Welcome to return to this guide. Use the checkbox at the bottom of Welcome to choose whether it opens after sign-in.

### Trying the live session

Choose **Live system** in the ISO boot menu to try Plasma. Changes in this session use temporary storage. Copy files you want to keep before powering off. The preview configures automatic live login for `kernova-live`. Debian live-config uses the temporary password `live`. The build requests a live account without administrative privileges.

To test installation in the project VM, restart with the same ISO and choose **Start installer** in the boot menu. Check the displayed disk size, name and proposed partition changes before confirming. The project VM has one new 40 GiB disk with serial KERNOVA-TEST. Use a new personal username, choose a password and complete the installer. Shut down and detach the ISO before starting the installed system. The first installation test is still pending.

### Personalize and work

Open System Settings to change colors, fonts, wallpaper, screen scale, or shortcuts. Select Breeze in Colors & Themes → Global Theme for a light desktop. Choose the Colors page to change the palette alone. Quick Settings offers an animation speed slider, including Instant. The default Plasma panel provides an application launcher, task manager, notifications, network, volume, clock and session actions.

Use Dolphin for files, Firefox ESR for browsing, Kate for text, Konsole for the terminal, Ark for archives, Okular for PDFs, Gwenview for images, Spectacle for screenshots, System Monitor for processes and VLC for media. These are the full preview's package selections. Internet access is needed to browse remote sites and refresh software indexes.

### Update an installed system

Back up your personal data to a second location. Open Discover and use Updates. Allow the current package operation to finish before starting another. To update using Konsole, refresh the package list with `sudo apt update`, then run `sudo apt upgrade`. Review the proposed changes before accepting. Restart after a kernel or important system update.

### Recover your work

If the desktop fails after a kernel update, select Advanced options for Debian GNU/Linux in the installed GRUB menu and boot a previous kernel if one is available. In Konsole inspect the current boot using `journalctl -b -p err` and failed units using `systemctl --failed`. Use `journalctl -b -1` for the previous boot if the journal was retained.

If the installed disk will not boot, start the ISO again. Use the installer’s advanced rescue option to identify the guest root filesystem and inspect it. For file recovery, mount the identified guest data volume read-only and copy important files to a separate backup target. An encrypted volume requires its passphrase. Restore a known-good backup when needed. APT and ext4 provide conventional package updates and filesystem storage. Keep independent backups for rollback and recovery.

### Credits

KERNOVA contributes the desktop defaults, Parallax artwork, Welcome and build integration. Debian, the Linux kernel project, KDE and the application maintainers supply the underlying system. Each installed Debian package carries its licensing information under `/usr/share/doc/<package>/copyright`.
