"""Catalogue validation, local-only requests, stream cancellation and verified imports."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/ai"))
import runtime


@contextmanager
def service(reply):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def dispatch(self):
            payload = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if self.headers.get("Content-Type") == "application/json":
                payload = json.loads(payload)
            requests.append((self.command, self.path, payload))
            reply(self, self.path, payload)

        do_GET = do_POST = do_DELETE = dispatch

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
        worker.start()
        client = runtime.Ollama()
        client.port = server.server_address[1]
        try:
            yield client, requests
        finally:
            server.shutdown()
            worker.join(2)


def respond(handler, *objects, status=200):
    handler.send_response(status)
    handler.end_headers()
    for entry in objects:
        handler.wfile.write(json.dumps(entry).encode() + b"\n")
        handler.wfile.flush()


def local_route(handler, path, payload):
    if path == "/api/tags":
        respond(handler, {"models": [{"name": "test:1b"}, {"name": "x:cloud"},
                                     {"name": "alias:latest", "remote_model": "other"}]})
    elif path == "/api/show":
        respond(handler, {"model_info": {"general.architecture": "toy", "toy.context_length": 512}})
    else:
        raise AssertionError(path)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.token = runtime.Cancellation()
        self.models = runtime._parse_catalog(runtime.BUNDLED_CATALOG.read_bytes())

    def test_catalog_size_independent_of_total_and_offline_fallback(self):
        model = dict(self.models[0], size=100_000_000_000)
        data = json.dumps({"version": 1, "models": [model]}).encode()
        with patch.dict("os.environ", KERNOVA_AI_CATALOG_URL="https://example.org/catalog.json"):
            with patch.object(runtime, "_open_https", return_value=io.BytesIO(data)):
                self.assertEqual(runtime.load_catalog(), ([model], ""))
            with patch.object(runtime, "_open_https", side_effect=OSError("offline")):
                self.assertEqual(runtime.load_catalog(), (self.models, "offline"))
        with patch.dict("os.environ", KERNOVA_AI_CATALOG_URL="http://example.org/catalog.json"):
            models, warning = runtime.load_catalog()
            self.assertEqual(models, self.models)
            self.assertTrue(warning)

    def test_catalog_rejects_foreign_registry_cloud_and_http_redirect(self):
        for changes in ({"tag": "foreign.tld/model:1b"}, {"tag": "test:cloud"}, {"tag": "test:7b-cloud"},
                        {"tag": "test@cloud"}, {"url": "https://foreign.tld/model:1b"}, {"size": -1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                runtime._validate_entry(dict(self.models[0], **changes))
        with self.assertRaises(ValueError):
            runtime._HTTPSRedirect().redirect_request(Request("https://example.org"), None, 302, "", {},
                                                       "http://example.org/redirect")

    def gguf(self, data):
        return dict(self.models[0], tag="example:latest", source="gguf", url="https://example.org/a.gguf",
                    size=len(data), sha256=hashlib.sha256(data).hexdigest())

    def test_gguf_bad_hash_blocks_upload_and_closes_temp(self):
        data = b"GGUF sample for digest testing"
        entry = dict(self.gguf(data), sha256="0" * 64)
        file = io.BytesIO()
        with patch.object(runtime, "_open_https", return_value=io.BytesIO(data)), \
                patch.object(runtime.tempfile, "TemporaryFile", return_value=file), \
                patch.object(runtime.Ollama, "_request") as request:
            with self.assertRaises(runtime.IntegrityError):
                runtime.Ollama().install(entry, self.token, lambda *_: None)
            request.assert_not_called()
            self.assertTrue(file.closed)

    def test_gguf_verified_bytes_uploaded_and_created_by_digest(self):
        data = b"GGUF sample for transport testing"
        entry = self.gguf(data)
        blob = "sha256:" + entry["sha256"]

        def route(handler, path, payload):
            respond(handler, {"status": "success"})

        with service(route) as (client, calls), patch.object(runtime, "_open_https", return_value=io.BytesIO(data)):
            client.install(entry, self.token, lambda *_: None)
            self.assertEqual(calls, [("POST", "/api/blobs/" + blob, data), ("POST", "/api/create", {
                "model": "example:latest", "files": {"model.gguf": blob}, "stream": True})])

    def test_discovery_distinguishes_installation(self):
        with service(local_route) as (client, calls):
            self.assertEqual(client.discover(), ("ready", ["test:1b"]))
        with patch.object(runtime, "_installed_binary", return_value=True):
            self.assertEqual(client.discover(), ("stopped", []))
        with patch.object(runtime, "_installed_binary", return_value=False):
            self.assertEqual(client.discover(), ("missing", []))

    def test_chat_filters_cloud_keeps_latest_turns_and_streams(self):
        def route(handler, path, payload):
            if path == "/api/chat":
                respond(handler, {"message": {"content": "one"}}, {"message": {"content": " two"}, "done": True})
            else:
                local_route(handler, path, payload)

        msgs = [{"role": role, "content": msg} for role, msg in (
            ("system", "support"), ("user", "old"), ("assistant", "x" * 500), ("user", "hello"),
            ("assistant", "hi"), ("user", "another question"))]
        with service(route) as (client, calls):
            with self.assertRaises(RuntimeError):
                client.chat("alias:latest", msgs, self.token, lambda _: None)
            self.assertEqual(len(calls), 1)
            parts = []
            client.chat("test:1b", msgs, self.token, parts.append)
            self.assertEqual(parts, ["one", " two"])
            payload = calls[-1][2]
            self.assertEqual(payload["messages"], [msgs[0]] + msgs[-3:])
            self.assertEqual(payload["model"], "test:1b:local")
            self.assertLessEqual(payload["options"]["num_ctx"], 512)
            with self.assertRaises(runtime.ContextTooLong):
                client.chat("test:1b", [{"role": "user", "content": "too long" * 500}], self.token, parts.append)

    def test_older_server_and_chat_rejects_remote_alias_details(self):
        def route(handler, path, payload):
            if path == "/api/show" and payload["model"].endswith(":local"):
                respond(handler, {"error": "invalid model path"}, status=500)
            elif path == "/api/show":
                respond(handler, {"remote_host": "https://example.org"})
            else:
                local_route(handler, path, payload)

        with service(route) as (client, calls):
            with self.assertRaisesRegex(RuntimeError, "installed local model"):
                client.chat("test:1b", [{"role": "user", "content": "private data"}], self.token, lambda _: None)
            self.assertEqual([call[1] for call in calls], ["/api/tags", "/api/show", "/api/show"])

    def test_structured_response_and_truncated_output_is_rejected(self):
        def route(handler, path, payload):
            if path == "/api/chat":
                respond(handler, {"message": {"content": "{}"}, "done": True, "done_reason": "length"})
            else:
                local_route(handler, path, payload)

        schema = {"type": "object"}
        with service(route) as (client, calls), self.assertRaises(runtime.ContextTooLong):
            try:
                client.chat("test:1b", [{"role": "user", "content": "x"}], self.token, lambda _: None,
                            response_format=schema)
            finally:
                self.assertEqual(calls[-1][2]["format"], schema)

    def test_stop_before_first_token_disconnects_server(self):
        waiting = threading.Event()
        closed = threading.Event()

        def route(handler, path, payload):
            if path == "/api/chat":
                handler.send_response(200)
                handler.end_headers()
                waiting.set()
                handler.connection.settimeout(5)
                try:
                    disconnected = not handler.connection.recv(1)
                except ConnectionResetError:
                    disconnected = True
                if disconnected:
                    closed.set()
            else:
                local_route(handler, path, payload)

        with service(route) as (client, calls), ThreadPoolExecutor(max_workers=1) as pool:
            job = pool.submit(client.chat, "test:1b", [{"role": "user", "content": "hi"}], self.token, lambda _: None)
            self.assertTrue(waiting.wait(3))
            self.token.cancel()
            with self.assertRaises(runtime.Cancelled):
                job.result(timeout=2)
            self.assertTrue(closed.wait(1))

    def test_pull_only_selected_model_retry_and_disk_full(self):
        entry = self.models[0]
        events = iter([[{"status": "pulling", "digest": "a", "completed": 40, "total": 100}],
                       [{"status": "pulling", "digest": "a", "completed": 70, "total": 100},
                        {"status": "pulling", "digest": "b", "completed": 10, "total": 20},
                        {"status": "success"}],
                       [{"error": "write: no space left on device"}]])

        def route(handler, path, payload):
            respond(handler, *next(events))

        progress = []
        with service(route) as (client, calls):
            with self.assertRaisesRegex(RuntimeError, "interrupted"):
                client.install(entry, self.token, lambda *step: progress.append(step))
            client.install(entry, self.token, lambda *step: progress.append(step))
            self.assertEqual(progress[-1][1], 80)
            with self.assertRaises(runtime.NoSpace):
                client.install(entry, self.token, lambda *_: None)
            self.assertTrue(all(call == ("POST", "/api/pull", {"model": entry["tag"], "stream": True})
                                for call in calls))

    def test_pull_custom_library_tag_normalizes_and_rejects_cloud_or_foreign(self):
        self.assertEqual(runtime.normalize_library_tag("llama3.2"), "llama3.2:latest")
        self.assertEqual(runtime.normalize_library_tag("ollama pull DeepSeek-R1:7B"), "deepseek-r1:7b")
        for bad in ("", "foreign.org/model:7b", "model:cloud", "model:7b-cloud", "user@model:1b"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                runtime.normalize_library_tag(bad)

        def route(handler, path, payload):
            respond(handler,
                    {"status": "pulling", "digest": "sha256:1", "completed": 50, "total": 200},
                    {"status": "success"})

        steps = []
        with service(route) as (client, calls):
            pulled = client.pull_tag("phi4", self.token, lambda *s: steps.append(s))
            self.assertEqual(pulled, "phi4:latest")
            self.assertEqual(calls, [("POST", "/api/pull", {"model": "phi4:latest", "stream": True})])
            self.assertEqual(steps[0], ("pulling", 50, 200))


if __name__ == "__main__":
    unittest.main()
