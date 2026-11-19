#!/bin/sh
# Plasma reads account preferences ahead of these distribution defaults.
case ":${XDG_CONFIG_DIRS:-/etc/xdg}:" in
    *:/etc/xdg/kernova:*) ;;
    *) export XDG_CONFIG_DIRS="/etc/xdg/kernova:${XDG_CONFIG_DIRS:-/etc/xdg}" ;;
esac
