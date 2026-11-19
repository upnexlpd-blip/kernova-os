# Kernova Crypto 0.1.11 verification

Verified on 19 November 2026.

## Native market data

On Windows with Python 3.12 and the existing PySide6 host runtime, the native
application loaded 526 active Binance Spot USDT markets and 96 BTC candles.
Selecting ETH and switching periods loaded 96, 168 and 180 candles for 24H, 7D
and 30D. Closing the window while a worker was still running completed without
late signal delivery. The preview used Qt offscreen rendering with the Windows
Segoe UI font.

The final Windows source check ran 51 tests with three platform-dependent skips.
It also passed Python compilation, shell syntax and ShellCheck. Regression tests
cover invalid market values, tiny prices, ordered candles, numeric sorting,
watchlist state, stale chart replies, provider retry windows, offline cache
validation and worker delivery after window close.

[Native preview](crypto-preview-windows.png)

## Debian packages and delivery

The Debian 13 build and test job passed for source c678942a on
[validation run 44597243607](https://github.com/upnexlpd-blip/kernova-os/actions/runs/44597243607).
The signed stable publication completed on
[run 44597730030](https://github.com/upnexlpd-blip/kernova-os/actions/runs/44597730030).

Windows independently verified InRelease against the previously embedded primary
fingerprint 7656A706E55A3F68686DE0FDB9EF5C29B22041E8, then verified the signed package
index and all five published package hashes. Inspection of kernova-desktop
0.1.11 confirmed the executable /usr/bin/kernova-crypto, the desktop menu entry
and both Python modules with the public market-data endpoint and shutdown guard.
The local audit is in build/crypto-stable-verification/verification.json in the
primary checkout.

## Scope

The application refreshes public prices every 15 seconds while open and charts
at most once per minute for an unchanged market and period. USDT is the quote
asset. Favorites and the latest price snapshot are stored in the user's account.
Source timestamps and connection interruptions are visible.

The published package integrates into the existing Preview profile. A new ISO
containing this version has not been built by this task. Interactive launch from
an installed Plasma desktop remains unverified. The live-data native preview,
Debian source tests, package build and signed-file inspection are the completed
checks.

[Binance public market-data interface](https://github.com/binance/binance-spot-api-docs/blob/master/faqs/market_data_only.md)
