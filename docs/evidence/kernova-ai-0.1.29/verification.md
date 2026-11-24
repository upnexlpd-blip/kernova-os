# KERNOVA AI 0.1.29 verification

Test date: 24 November 2026. The source baseline was `14215fb` of `upnexlpd-blip/kernova-os`.

## Debian package

The dedicated Debian 13 amd64 builder ran `scripts/build-packages` as an ordinary user. The binary `kernova-ai_0.1.29_all.deb` is 49,474 bytes, architecture `all`, SHA-256 `e9b3465c9dfd6137dcf835026d6f9e2e7ec7412ffa0b75b5858e850456a41969`. Its Python modules, catalog, locales, menu entry, executable launcher, artwork and guide matched the checkout. The package contains no model weights. APT installed it alongside the released `kernova-performance` 0.1.25.

On Debian 13.8, kernel 6.12.118+deb13-cloud-amd64 and PySide6 6.8.2.1, both `kernova-ai` and `gio launch /usr/share/applications/kernova-ai.desktop` opened a 1220 × 590 window on X11. `apt-get check` and `dpkg -V kernova-ai` passed. `scripts/check-source` compiled 73 Python sources, checked 13 shell entry points and passed ShellCheck, desktop-file-validate and all 122 tests in the repository, including 30 AI checks. The test run took 47.846 seconds. Build and validation logs are next to the local package in `artifacts/ai-0.1.29/`.

The physical RTX tests used Windows. The remaining hardware checks on an installed KERNOVA Plasma desktop are NVIDIA acceleration with its Linux driver and unmuting a physical audio output after confirmation.

## Desktop and GPU

The Windows host ran Python 3.12.14, PySide6 6.8.2.1, Ollama 0.40.18 and an NVIDIA GeForce RTX 3060 with 12,288 MiB. The desktop tests used actual Qt widgets, an isolated chat database and the local Ollama HTTP service. The screenshots use Qt's Windows platform plugin. A fresh profile opened the English light interface. Saving Dark in Settings changed the running window and reopening the application restored the selection. [Light home screen](home-light.png) · [Dark home screen](home-dark.png)

| Procedure | Observed result |
| --- | --- |
| Start another real Ollama process with an empty model directory on a temporary loopback port. Open the first-run window and library. | **Избери модел** was visible, Send was disabled and all three catalog entries were available. The library displayed the purpose, size, license and source for the selected entry. [Catalog](catalog-mk.png) |
| On the existing Ollama at 127.0.0.1:11434, select and download only `qwen2.5-coder:7b` through the library. Inspect tags before and after. | The initial list contained `gemma4:12b`. Progress reached 4.68 GB and the tag list gained only `qwen2.5-coder:7b` (`dae161e27b0e`). During inference `ollama ps` showed 100% GPU and a context of 16,384. |
| Ask the downloaded model to remember MARIGOLD. Ask for the word in a second turn. Request a long answer and click Stop after the first visible text. Close and reopen the database and the window, then select the conversation. | Both replies contained MARIGOLD. Stop returned the UI to idle in 15 ms in the final package run. The reopened conversation contained seven messages and activity entries, including the interrupted reply. |
| Ask Support in Macedonian why the disk is full, then ask the difference between RAM and disk storage. | In the final package run the disk had 807.5 GiB free of 930.4 GiB. The direct capacity answer used the same measurement and correctly described adequate free space. The follow-up question used the local model. [Support conversation](support-rtx3060.png) |
| Select the pre-existing `gemma4:12b` from the same store, repeat the two-turn memory check, interrupt a long response, reopen history. | Both turns returned the stored word. Stop completed in 31 ms and the seven history entries reopened successfully. |
| Create a temporary local alias of the downloaded model. In the library, request deletion of that alias, cancel, then repeat and confirm. | The alias survived cancellation. After confirmation the alias disappeared, and the tags matched the original local model list exactly. |
| Choose a temporary project containing `colors.py`. Ask the downloaded model to replace amber with violet. Inspect and reject the first proposal. Repeat and apply the second. | The original bytes were present during each review and after rejection. Apply changed the file to print violet. The reviewed diff and the user's decision appeared in the history. [Diff before applying](code-review-rtx3060.png) |

## Custom GGUF source

The source fixture was the [revision-pinned TinyStories GGUF](https://huggingface.co/ggml-org/models/resolve/499bc8821c6b12b4e53c5bffcb21ec206f212d81/tinyllamas/stories260K.gguf), 1,185,376 bytes. With a declared digest of 64 zeroes, verification failed before upload, the test tag was absent and the temporary directory was empty. With the digest below, the real Ollama service parsed the GGUF, wrote the manifest and listed the new tag. Deleting the temporary QA tag succeeded. Both runs left the download directory empty.

```text
270cba1bd5109f42d03350f60406024560464db173c0e387d91f0426d3bd256d
```

## Offline inference

A private Ollama 0.40.18 instance on the RTX host reused the downloaded 7B model's blobs through hard links in a temporary store. Cloud was disabled and its HTTP and HTTPS proxy pointed at a closed local port. A registry request failed with a proxy connection refusal. Immediately afterward `qwen2.5-coder:7b` answered `42` through the application's local chat client. The host retained its usual network connection.

A second Debian 13 guest booted with no emulated network adapter. The test enabled only loopback, verified empty IPv4 and IPv6 route tables and checked that an external connection returned `ENETUNREACH`. An unprivileged Ollama 0.6.6 process loaded the previously downloaded TinyStories GGUF. The application's production client received 512 fragments from `/api/chat` in 13.26 seconds. This guest used CPU inference. [Procedure and console transcript](offline.txt)
