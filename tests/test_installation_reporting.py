"""Installation reporting must be explicit, retryable and excluded from Live."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/welcome"))
import installation_registration as reporting


class InstallationReportingTests(unittest.TestCase):
    def test_service_validation(self):
        for address in ("http://example.com", "https://user:pass@example.com", "https://example.com/path", "file:///tmp/test"):
            with self.assertRaises(ValueError):
                reporting.endpoint_url(address)
        self.assertEqual(reporting.endpoint_url("https://example.com/"), "https://example.com")
        self.assertEqual(reporting.endpoint_url("http://127.0.0.1:8783"), "http://127.0.0.1:8783")

    def test_live_and_unknown_never_send(self):
        for cmdline in ("boot=live quiet", None):
            with patch.object(reporting, "read_text", return_value=cmdline), patch.object(reporting, "urlopen") as network:
                with self.assertRaises(ValueError):
                    reporting.report("https://example.com", "0.1.7")
                network.assert_not_called()

    def test_retry_reuses_identity_and_withdraws(self):
        with TemporaryDirectory() as directory:
            state = Path(directory) / "registration.json"
            product = Path(directory) / "product.json"
            product.write_text('{"slug":"kernova-os"}')
            response = MagicMock()
            response.__enter__.return_value.read.return_value = b'{"ok":true}'
            with patch.object(reporting, "PRODUCT", product), patch.object(reporting, "read_text", return_value="quiet"), patch.object(reporting, "urlopen", return_value=response) as network:
                reporting.report("https://example.com", "0.1.7", state_path=state)
                first = json.loads(state.read_text())
                reporting.report("https://example.com", "0.1.7", state_path=state)
                self.assertEqual(first, json.loads(state.read_text()))
                payload = json.loads(network.call_args.args[0].data)
                self.assertEqual(set(payload), {"id", "secret", "version", "session", "consent"})
                self.assertTrue(payload["consent"])
                reporting.report("https://example.com", "0.1.7", withdraw=True, state_path=state)
                self.assertTrue(network.call_args.args[0].full_url.endswith("/withdraw"))
                self.assertEqual(first, json.loads(state.read_text()))


if __name__ == "__main__":
    unittest.main()
