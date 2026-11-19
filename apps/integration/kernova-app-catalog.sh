#!/bin/sh
# Set up the account's local Flatpak source before Plasma starts any Discover process.
# Initialization reads the bundled key offline. Discover fetches the catalog on demand.
/usr/bin/kernova-get-apps --initialize || :
