# Your KERNOVA desktop

KERNOVA OS uses KDE Plasma on Debian 13. Open the application launcher with the Meta key. Search for KERNOVA Welcome to return to this guide. Use the checkbox at the bottom of Welcome to choose whether it opens after sign-in.

### System Help

Open Konsole in your Plasma session and run `kernova-doctor scan`. The command reads local network, playback, package, root filesystem and Adaptive Engine state. Use `kernova-doctor scan --json` for a structured report, or `kernova-doctor check audio` for just the selected output. The other areas are `network`, `updates`, `disk` and `adaptive`. An optional `kernova-doctor check network --online` also contacts Debian over HTTPS with a four-second timeout.

If the default output is muted, run `kernova-doctor fix audio.unmute`. Match the output number to `wpctl status` and type `yes` to confirm. The command checks the selected output again, clears mute and reads the result. Play a local sound to verify the speakers or headphones.

### Trying the live session

Choose **Live system** in the ISO boot menu to try Plasma. Changes in this session use temporary storage. Copy files you want to keep before powering off. The preview configures automatic live login for `kernova-live`. Debian live-config uses the temporary password `live`. The build requests a live account without administrative privileges.

On the preview live desktop open **Install KERNOVA OS** to start the wizard. Choose your language, location, keyboard and disk. **Erase disk** removes the contents of the selected disk. **Install alongside** is offered when an existing partition can be shrunk. Use manual partitioning for space already marked unallocated. On **Users**, choose your own username and password. Review the proposed changes, then confirm. The project test VM has a 40 GiB disk with serial KERNOVA-TEST. Detach the ISO before starting the installed guest. The boot menu also offers Debian’s graphical **Start installer**.

### Personalize and work

Open System Settings to change colors, fonts, wallpaper, screen scale, or shortcuts. Select Breeze in Colors & Themes → Global Theme for a light desktop. Choose the Colors page to change the palette alone. Quick Settings offers an animation speed slider, including Instant. The default Plasma panel provides an application launcher, task manager, notifications, network, volume, clock and session actions.

Use Dolphin for files, Firefox ESR for browsing, Kate for text, Konsole for the terminal, Ark for archives, Okular for PDFs, Gwenview for images, Spectacle for screenshots, System Monitor for processes and VLC for media. These are the full preview's package selections. Internet access is needed to browse remote sites and refresh software indexes.

Search the Plasma menu for **App Download** to open Discover. Choose a Flathub listing and select **Install**. Applications from this source are installed for your account. You can find **Google Chrome**, **Viber**, **Telegram**, and **ZapZap** there. ZapZap is an independent client for WhatsApp Web. In the Live session, downloads and sign-ins use temporary storage. The App Download launcher's context menu also offers Google's own Chrome download page in Firefox.

Search for **Drivers** to see the processor and graphics hardware detected by Linux. The preview includes AMD and Intel CPU microcode, Mesa, and AMD, Intel and NVIDIA graphics firmware. The download buttons open Debian's pages for the selected hardware. On an installed system use **Discover → Updates** to update the packaged kernel, firmware and graphics components. A QEMU guest shows its virtual graphics adapter. To change the desktop background, right-click an empty area of the desktop, open its wallpaper settings and choose one of the KERNOVA photographs.

Open **AI Tools** from the menu for Codex CLI, Claude Code, Cursor or Alpaca. On KERNOVA 0.1.10 and later, select **Install** for Codex CLI or Claude Code and follow the progress in the same window. Select **Open in Konsole** when the installation finishes. Earlier releases open the installer directly in Konsole. Cursor offers a Debian x64 package. Alpaca opens in Discover and can download local models. Keep large model files on an installed system with enough free disk space.

Open **KERNOVA Welcome → Settings** to find Wi-Fi, Ethernet, Bluetooth, display, sound, power, appearance, applications, notifications, search and online accounts. To test a physical wireless adapter, boot the Live USB on the computer, join a Wi-Fi network and open a website with Ethernet disconnected. For Bluetooth, pair a device and exercise it, such as playing audio on headphones. Internet through the virtual Ethernet adapter in QEMU tests the VM network.

### Control the desktop from a phone

Connect the phone to the same trusted home network as the computer. Open **KERNOVA Welcome → Getting started → Connect phone**. If Plasma asks which screen to share, select the screen you want to control and allow sharing.

In **RealVNC Viewer** on Android or iPhone, add a direct connection using the computer’s Wi-Fi or Ethernet IP address and the port shown in Krfb. Enter Krfb’s **desktop sharing password**. On the computer, allow remote control and accept the incoming connection. Leave **Enable Unattended Access** unchecked so each connection asks for approval.

Turn off **Enable Desktop Sharing** in Krfb to disconnect the phone and stop accepting connections. Closing the window can leave Krfb in the system tray. Use this feature on a trusted LAN because a direct VNC session can carry screen and keyboard data without encryption.

### Weather

Search the application menu for **KERNOVA Weather**. **Use my location** asks the system for a position, including GPS when available, and opens the forecast for the nearest city. **Open Weather** opens the native GNOME Weather window where you can search for a city, revisit saved places, and switch between hourly and daily forecasts. Refreshing the forecast requires internet access. The temperature next to the clock follows the most recently selected saved city. Click it to open that forecast.

### Update an installed system

Back up your personal data to a second location. Open Discover and use Updates. Allow the current package operation to finish before starting another. To update using Konsole, refresh the package list with `sudo apt update`, then run `sudo apt upgrade`. Review the proposed changes before accepting. Restart after a kernel or important system update.

### Recover your work

If the desktop fails after a kernel update, select Advanced options for Debian GNU/Linux in the installed GRUB menu and boot a previous kernel if one is available. In Konsole inspect the current boot using `journalctl -b -p err` and failed units using `systemctl --failed`. Use `journalctl -b -1` for the previous boot if the journal was retained.

If the installed disk will not boot, start the ISO again. Use the installer’s advanced rescue option to identify the guest root filesystem and inspect it. For file recovery, mount the identified guest data volume read-only and copy important files to a separate backup target. An encrypted volume requires its passphrase. Restore a known-good backup when needed. APT and ext4 provide conventional package updates and filesystem storage. Keep independent backups for rollback and recovery.

### Kernova Crypto

Open **Kernova Crypto** from the application menu to follow Binance Spot markets
quoted in USDT. Prices refresh every 15 seconds while the window is open.
Select a market for 24-hour, 7-day or 30-day candlestick charts. Use the Watch
checkbox to save a market and choose Watchlist to filter your saved markets.
Search and numeric column sorting work on the current snapshot.

The status shows when a snapshot was received and the provider's market timestamp.
On connection failure the app retains the previous snapshot and marks the
interruption. Provider rate limits temporarily pause requests. The newest candle
can still change. Preferences and an offline snapshot are saved in your account.

Data comes from Binance's public market-data service. USDT is the quote asset.
[Binance public market-data documentation](https://github.com/binance/binance-spot-api-docs/blob/master/faqs/market_data_only.md)

### Credits

KERNOVA contributes the desktop defaults, Parallax artwork, Welcome and build integration. Debian, the Linux kernel project, KDE and the application maintainers supply the underlying system. Each installed Debian package carries its licensing information under `/usr/share/doc/<package>/copyright`.
