# KERNOVA AI on Debian 13

Install the application package from the directory containing the downloaded Debian file. The package uses KERNOVA's existing Debian and KERNOVA APT sources for its dependencies.

```sh
sudo apt install ./kernova-ai_0.1.29_all.deb
kernova-ai
```

Open **KERNOVA AI** from the application menu. The first launch uses English and the light theme. Choose **Settings → Appearance → Dark → Save** for the black interface. Settings also offers Macedonian. Run `kernova-ai --language mk` or `kernova-ai --language en` for a one-time language override.

The local Ollama service must be available at `127.0.0.1:11434`. For a new installation, follow the official Linux instructions, then use **Check again**. With an existing systemd installation, `sudo systemctl start ollama` starts the service. Run the desktop program from the ordinary Plasma account. [Ollama for Linux](https://docs.ollama.com/linux)

## Models and history

The first download requires internet access. From **Models** choose one tag and download it. Retry a registry download to reuse completed data. The application discovers installed local models through Ollama and shares the selected copy between the Chat, Support and Code tabs. Type a message and press Enter or the send arrow. Shift+Enter adds a line. During generation the arrow becomes a Stop button. Model deletion requires confirmation and affects other clients using that Ollama instance. Conversations are stored under `$XDG_DATA_HOME/kernova-ai/history.sqlite3`, defaulting to `~/.local/share/kernova-ai/history.sqlite3`. The sidebar has a separate action to delete a conversation.

| Model | Download | Intended use | License |
| --- | ---: | --- | --- |
| [qwen2.5-coder:7b](https://ollama.com/library/qwen2.5-coder:7b) | 4.68 GB | Coding on the 12 GB RTX 3060 | Apache-2.0 |
| [qwen2.5-coder:3b](https://ollama.com/library/qwen2.5-coder:3b) | 1.93 GB | Lighter coding model | Qwen Research License, non-commercial research and evaluation |
| [qwen2.5:1.5b](https://ollama.com/library/qwen2.5:1.5b) | 0.99 GB | Multilingual chat and Support | Apache-2.0 |

Ollama manages model weights in its own store. The KERNOVA package and ISO contain the catalog only. The Code tool reads one selected UTF-8 text file per request. Large files or requests that exceed the model context produce a size message. The application keeps the current request and fits recent complete turns within a conservative context budget.

## Optional hosted catalog

The bundled catalog works offline. Set `catalog_url` in `/etc/kernova/ai.json` to the HTTPS address of a raw JSON catalog, or set `KERNOVA_AI_CATALOG_URL` for a single process. The application fetches that address when opening the library. An invalid or unavailable catalog falls back to the bundled copy. Copy `apps/ai/catalog.json` as the version 1 template. Registry entries use a plain official library tag and its matching Ollama URL. Adding entries to the catalog downloads no weights.

For a self-hosted GGUF add an entry like the one below with your real URL, exact byte count and lowercase SHA-256, obtainable with `stat -c %s model.gguf` and `sha256sum model.gguf`. Use an unused local tag. Replace all example values before distributing the catalog.

```json
{
  "tag": "kernova-example:v1",
  "source": "gguf",
  "url": "https://models.example.org/model.gguf",
  "size": 123456789,
  "sha256": "<64 lowercase hexadecimal characters>",
  "license": "<model license>",
  "purpose": {"en": "General chat", "mk": "Општ разговор"}
}
```

The selected GGUF downloads into a temporary file. The application verifies both the length and the digest before uploading the blob to Ollama and creating the local tag. Allow space for the temporary download and Ollama’s store. A failed verification discards the temporary file. Retrying a GGUF download starts it again.
