"""Local Ollama operations. Call blocking operations on a worker thread."""

from contextlib import contextmanager
import errno
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import socket
import tempfile
import threading
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler


BUNDLED_CATALOG = Path(__file__).with_name("catalog.json")
CONFIG = Path("/etc/kernova/ai.json")
MAX_CATALOG = 1024 * 1024
MAX_RESPONSE = 8 * 1024 * 1024
TAG = re.compile(r"[a-z0-9][a-z0-9_.-]{0,126}:[a-z0-9][a-z0-9_.-]{0,126}")


class Cancelled(RuntimeError):
    pass


class IntegrityError(RuntimeError):
    pass


class NoSpace(RuntimeError):
    pass


class ContextTooLong(RuntimeError):
    pass


class _OllamaHTTPError(RuntimeError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class Cancellation:
    """Interrupt the connection, including a reader waiting for the first token."""

    def __init__(self):
        self._lock = threading.Lock()
        self._cancelled = False
        self._socket = None

    def cancel(self):
        with self._lock:
            self._cancelled = True
            if self._socket is not None:
                try:
                    self._socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

    def check(self):
        with self._lock:
            if self._cancelled:
                raise Cancelled("Request stopped.")

    @contextmanager
    def watching(self, sock):
        with self._lock:
            if self._cancelled:
                raise Cancelled("Request stopped.")
            self._socket = sock
        try:
            yield
        except GeneratorExit:
            raise
        except Exception:
            self.check()
            raise
        else:
            self.check()
        finally:
            with self._lock:
                self._socket = None


def _https(url):
    if not isinstance(url, str) or len(url) > 4096 or any(c.isspace() for c in url):
        raise ValueError("Invalid HTTPS URL.")
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username is not None or parts.fragment:
        raise ValueError("An HTTPS URL without embedded credentials is required.")
    return url


class _HTTPSRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, _https(newurl))


def _open_https(url):
    return build_opener(_HTTPSRedirect()).open(_https(url), timeout=20)


def _read_limited(stream, limit):
    result = stream.read(limit + 1)
    if len(result) > limit:
        raise ValueError("Response is too large.")
    return result


def _cloud_name(tag):
    suffix = tag.lower().rsplit(":", 1)[-1]
    return suffix == "cloud" or suffix.endswith("-cloud") or "@" in tag


def _validate_entry(entry):
    if not isinstance(entry, dict):
        raise ValueError("Invalid model entry.")
    tag = entry.get("tag")
    if not isinstance(tag, str) or not TAG.fullmatch(tag) or _cloud_name(tag):
        raise ValueError("Expected a local model name:tag.")
    if type(entry.get("size")) is not int or entry["size"] <= 0:
        raise ValueError("Missing download size.")
    purpose = entry.get("purpose")
    if not isinstance(purpose, dict):
        raise ValueError("Missing model purpose.")
    for value in [entry.get("license"), purpose.get("en"), purpose.get("mk")]:
        if not isinstance(value, str) or not value.strip() or len(value) > 2048:
            raise ValueError("Invalid model description or license.")
    url = _https(entry.get("url"))
    if entry.get("source") == "registry":
        if url != "https://ollama.com/library/" + tag:
            raise ValueError("Expected the official Ollama model page.")
    elif entry.get("source") == "gguf":
        checksum = entry.get("sha256")
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError("GGUF requires a lowercase SHA-256 digest.")
    else:
        raise ValueError("Unknown model source.")


def _parse_catalog(data):
    doc = json.loads(data)
    if not isinstance(doc, dict) or doc.get("version") != 1 or not isinstance(doc.get("models"), list):
        raise ValueError("Invalid catalogue version or model list.")
    seen = set()
    for entry in doc["models"]:
        _validate_entry(entry)
        if entry["tag"] in seen:
            raise ValueError("Duplicate model name.")
        seen.add(entry["tag"])
    return doc["models"]


def load_catalog():
    models = _parse_catalog(BUNDLED_CATALOG.read_bytes())
    try:
        url = os.environ.get("KERNOVA_AI_CATALOG_URL")
        if not url and CONFIG.is_file():
            with CONFIG.open("rb") as f:
                config = json.loads(_read_limited(f, 16 * 1024))
            if not isinstance(config, dict):
                raise ValueError("Invalid catalogue configuration.")
            url = config.get("catalog_url")
        if url:
            with _open_https(url) as stream:
                models = _parse_catalog(_read_limited(stream, MAX_CATALOG))
    except (OSError, ValueError, http.client.HTTPException) as error:
        return models, str(error)
    return models, ""


def _error(message, status=None):
    msg = str(message)[:2048]
    if any(s in msg.lower() for s in ("no space left", "not enough space", "disk full", "disk quota exceeded")):
        raise NoSpace(msg)
    if status is not None:
        raise _OllamaHTTPError(status, msg)
    raise RuntimeError(msg)


def _history(messages, context, *, structured=False):
    """Budget one token per UTF-8 byte plus role/template overhead, keeping complete recent turns."""
    def cost(message):
        return len(message["content"].encode("utf-8")) + 32

    if not messages or messages[-1]["role"] != "user":
        raise ValueError("Expected a final user message.")
    prefix = []
    turns = []
    for message in messages:
        role = message["role"]
        if role == "system" and not turns:
            prefix.append(message)
        elif role == "user":
            turns.append([message])
        elif role == "assistant" and turns:
            turns[-1].append(message)
        else:
            raise ValueError("Invalid conversation order.")
    reply_tokens = min(4096 if structured else 1024, context // 4)
    remaining = context - reply_tokens - 64 - sum(map(cost, prefix))
    first = len(turns)
    for turn in reversed(turns):
        remaining -= sum(map(cost, turn))
        if remaining < 0:
            break
        first -= 1
    if first == len(turns):
        raise ContextTooLong("The message and its attachments exceed the model context.")
    return prefix + [msg for turn in turns[first:] for msg in turn], reply_tokens


def _installed_binary():
    return bool(shutil.which("ollama") or any(path.is_file() for path in (
        Path("/usr/local/bin/ollama"), Path("/usr/bin/ollama"),
        Path("/etc/systemd/system/ollama.service"), Path("/usr/lib/systemd/system/ollama.service"),
        Path(os.environ.get("LOCALAPPDATA", "/nonexistent")) / "Programs/Ollama/ollama.exe",
    )))


class Ollama:
    port = 11434

    @contextmanager
    def _request(self, method, path, token, *, payload=None, file=None, size=None, timeout=600):
        token.check()
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        headers = {}
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif file is not None:
            body = file
            headers = {"Content-Type": "application/octet-stream", "Content-Length": str(size)}
        try:
            conn.connect()
            conn.sock.settimeout(timeout)
            with token.watching(conn.sock):
                conn.request(method, path, body, headers)
                with conn.getresponse() as response:
                    if not 200 <= response.status < 300:
                        data = response.read(8192).decode(errors="replace")
                        try:
                            data = json.loads(data)["error"]
                        except (ValueError, KeyError, TypeError):
                            pass
                        _error(data or f"Ollama HTTP {response.status}", response.status)
                    yield response
        finally:
            conn.close()

    def _json(self, method, path, token, payload=None):
        with self._request(method, path, token, payload=payload, timeout=20) as stream:
            data = json.loads(_read_limited(stream, MAX_RESPONSE))
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected Ollama response.")
        if "error" in data:
            _error(data["error"])
        return data

    def _events(self, path, payload, token):
        with self._request("POST", path, token, payload=payload) as stream:
            while True:
                token.check()
                line = stream.readline(MAX_RESPONSE + 1)
                if not line:
                    break
                if len(line) > MAX_RESPONSE:
                    raise RuntimeError("Ollama event is too large.")
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise RuntimeError("Unexpected Ollama event.")
                if "error" in event:
                    _error(event["error"])
                yield event

    def _names(self, token):
        result = self._json("GET", "/api/tags", token)
        if not isinstance(result.get("models"), list):
            raise RuntimeError("Ollama did not return its local model list.")
        names = []
        for entry in result["models"]:
            name = entry.get("name") or entry.get("model")
            if isinstance(name, str) and not (_cloud_name(name) or entry.get("remote_model") or entry.get("remote_host")):
                names.append(name)
        return sorted(names)

    def discover(self):
        try:
            return "ready", self._names(Cancellation())
        except (ConnectionRefusedError, TimeoutError):
            return ("stopped" if _installed_binary() else "missing"), []

    def chat(self, tag, messages, token, on_text, *, response_format=None):
        if tag not in self._names(token):
            raise RuntimeError("Select an installed local model.")
        # Servers with source-qualified names reject cloud aliases atomically at generation time.
        request_name = tag + ":local"
        try:
            details = self._json("POST", "/api/show", token, {"model": request_name})
        except _OllamaHTTPError as error:
            invalid_path = error.status == 500 and str(error).lower() == "invalid model path"
            if error.status not in (400, 404) and not invalid_path:
                raise
            # Older releases accept only the bare name returned by /api/tags.
            request_name = tag
            details = self._json("POST", "/api/show", token, {"model": tag})
        if details.get("remote_host") or details.get("remote_model"):
            raise RuntimeError("Select an installed local model.")
        info = details.get("model_info", {})
        maximum = info.get(str(info.get("general.architecture")) + ".context_length", 4096)
        if type(maximum) != int or maximum < 256:
            raise RuntimeError("Invalid model context length.")
        context = min(maximum, 16384)
        history, reply_tokens = _history(messages, context, structured=response_format is not None)
        body = {"model": request_name, "messages": history, "stream": True,
                "options": {"num_ctx": context, "num_predict": reply_tokens}}
        thinking = details.get("thinking")
        if isinstance(thinking, dict) and any(v is False for v in thinking.get("values", [])):
            body["think"] = False
        if response_format is not None:
            body["format"] = response_format
        received_text = False
        for event in self._events("/api/chat", body, token):
            chunk = event.get("message", {}).get("content", "")
            if chunk:
                received_text = True
                on_text(chunk)
            token.check()
            if event.get("done") is True:
                if response_format is not None and event.get("done_reason") == "length":
                    raise ContextTooLong("The proposed edit exceeds the model output budget.")
                if not received_text:
                    raise RuntimeError("The model finished without returning an answer.")
                return
        raise RuntimeError("Chat stream ended before completion.")

    def install(self, entry, token, progress):
        _validate_entry(entry)
        if entry["source"] == "gguf":
            self._import_gguf(entry, token, progress)
            return
        layers = {}
        for event in self._events("/api/pull", {"model": entry["tag"], "stream": True}, token):
            digest, total = event.get("digest"), event.get("total")
            if digest and isinstance(total, int):
                layers[digest] = min(total, event.get("completed", 0))
            status = event.get("status", "")
            progress(status, sum(layers.values()), entry["size"])
            if status == "success":
                return
        raise RuntimeError("Download interrupted. Retry to resume.")

    def _import_gguf(self, entry, token, progress):
        token.check()
        expected = entry["size"]
        digest = hashlib.sha256()
        with tempfile.TemporaryFile("w+b") as temp:
            if shutil.disk_usage(tempfile.gettempdir()).free < expected:
                raise NoSpace("Insufficient temporary disk space for the selected GGUF.")
            downloaded = 0
            try:
                with _open_https(entry["url"]) as stream:
                    while True:
                        token.check()
                        chunk = stream.read(1024 * 1024)
                        if not chunk:
                            break
                        downloaded += len(chunk)
                        if downloaded > expected:
                            raise IntegrityError("GGUF download exceeds the declared size.")
                        temp.write(chunk)
                        digest.update(chunk)
                        progress("Downloading GGUF", downloaded, expected)
                temp.flush()
            except OSError as error:
                if error.errno in (errno.ENOSPC, getattr(errno, "EDQUOT", errno.ENOSPC)):
                    raise NoSpace(str(error)) from error
                raise
            token.check()
            if downloaded != expected or digest.hexdigest() != entry["sha256"]:
                raise IntegrityError("GGUF size or SHA-256 verification failed.")
            blob = "sha256:" + entry["sha256"]
            temp.seek(0)
            progress("Importing GGUF", downloaded, expected)
            with self._request("POST", "/api/blobs/" + blob, token, file=temp, size=expected):
                pass
            payload = {"model": entry["tag"], "files": {"model.gguf": blob}, "stream": True}
            for event in self._events("/api/create", payload, token):
                status = event.get("status", "")
                progress(status, downloaded, expected)
                if status == "success":
                    return
        raise RuntimeError("GGUF import ended before completion.")

    def delete(self, tag):
        token = Cancellation()
        if tag not in self._names(token):
            raise RuntimeError("Select an installed local model.")
        with self._request("DELETE", "/api/delete", token, payload={"model": tag}):
            pass
