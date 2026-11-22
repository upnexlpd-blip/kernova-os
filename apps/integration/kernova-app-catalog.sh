#!/bin/sh
# Set up the account's local Flatpak source before Plasma starts any Discover process.
# Initialization reads the bundled key offline. Discover fetches the catalog on demand.
if [ ! -e "${XDG_STATE_HOME:-$HOME/.local/state}/kernova/flathub-initialized" ] ||
   [ ! -e "${XDG_STATE_HOME:-$HOME/.local/state}/kernova/viber-xcb-initialized" ]; then
    # A stalled Flatpak operation must eventually release the login. Missing
    # markers cause the catalog launcher or the next login to retry.
    /usr/bin/timeout --kill-after=2s 10s /usr/bin/kernova-get-apps --initialize || :
fi
