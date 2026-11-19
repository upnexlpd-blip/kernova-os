# Local Debian builder on Windows

The reference Windows 11 computer runs Debian 13 amd64 under QEMU with four vCPUs, 8 GiB RAM and an 80 GiB virtual disk at `D:\KERNOVA-VM\debian13-builder\debian13.qcow2`. The first build used software emulation. AMD SVM and Windows Hypervisor Platform enabled WHPX on 19 November 2026.

## Local console

In PowerShell, open the local project directory and run `& .\build\windows-builder\start-builder.ps1 -Console` when the VM is stopped. The builder uses a local console and a separate Live guest for graphical testing. Source enters the builder on a read-only virtual CD and the release returns through a virtual serial port. SSH is disabled.

Log in as `builder`. On the original host, `python -B .\build\windows-builder\local-login.py` displays the initial DPAPI-protected password. Change it inside Debian with `passwd`. Run `sudo systemctl poweroff` to shut down the builder. The host-specific helpers and private VM disk are generated locally and excluded from Git.

## Monitor a build

```powershell
$vm = Get-Content -Raw 'D:\KERNOVA-VM\debian13-builder\current-run.json' | ConvertFrom-Json
Get-Content -LiteralPath (Join-Path $vm.logs 'serial.log') -Tail 12 -Wait
```

Ctrl+C ends the log viewer. In the builder, each run has a build.log and publishes its ISO, SHA256SUMS, manifest and validation report under artifacts.

## Run the Live desktop

On the reference host, open **KERNOVA Live.cmd** under Desktop\OS. It selects the latest local Preview, checks its checksum and opens QEMU. Select **Live system** and use **Meta+E** to open Dolphin. **Ctrl+Alt+G** releases the pointer. The preview uses SDL for audio. Power off from Plasma when finished.

## Tool provenance

The builder started with Debian's `debian-13-genericcloud-amd64-20261116-2664.qcow2`. Its SHA-512 matched manifests from two Debian HTTPS endpoints. The cloud image did not have a separate OpenPGP signature. Packages and installer inputs were checked against signed Debian archive metadata. [Debian cloud images](https://cloud.debian.org/images/cloud/)

The QEMU Windows build from 11 August 2026 matched the published SHA-512. Windows reported that its Authenticode certificate was outside its validity period. [QEMU downloads](https://www.qemu.org/download/#windows) · [Build checksum](https://qemu.weilnetz.de/w64/2026/qemu-w64-setup-20260811.sha512)
