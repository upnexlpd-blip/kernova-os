"""Market validation, chart request races, watchlists and numeric ordering."""
import importlib.util
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from email.message import Message
from threading import Event
from urllib.error import HTTPError
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "apps/crypto"
sys.path.insert(0, str(APP))
from market_data import MarketError, Ticker, candles, parse_tickers, price, request_json


class MarketDataTests(unittest.TestCase):
    def test_small_prices_are_visible(self):
        self.assertEqual(float(price(0.0000000002)), 0.0000000002)

    def test_long_provider_retry_window_is_honored(self):
        headers = Message()
        headers["Retry-After"] = "172800"
        error = HTTPError("https://example.test", 429, "Rate limit", headers, None)
        with patch("market_data.urlopen", side_effect=error):
            with self.assertRaises(MarketError) as caught:
                request_json("ticker/24hr")
        self.assertEqual(caught.exception.retry_after, 172800)

    def test_only_active_valid_markets_are_shown(self):
        base = dict(symbol="BTCUSDT", lastPrice="100", priceChangePercent="-2",
                    quoteVolume="1000", highPrice="110", lowPrice="90", closeTime=1000)
        self.assertEqual(parse_tickers([base], {"BTCUSDT": "BTC"})[0].price, 100)
        for field, bad in (("lastPrice", "NaN"), ("lastPrice", "0"),
                           ("quoteVolume", "-1"), ("highPrice", "80")):
            with self.assertRaises(MarketError):
                parse_tickers([{**base, field: bad}], {"BTCUSDT": "BTC"})
        with self.assertRaises(MarketError):
            parse_tickers([base], {"ETHUSDT": "ETH"})

    def test_candles_must_be_ordered_and_finite(self):
        valid = [[1000, "10", "12", "8", "11", "5"], [2000, "11", "13", "9", "12", "6"]]
        with patch("market_data.request_json", return_value=valid):
            self.assertEqual(len(candles("BTCUSDT", "24H")), 2)
        for invalid in (valid[::-1], valid[:1], [[1000, "NaN", "12", "8", "11", "5"]] * 2):
            with patch("market_data.request_json", return_value=invalid), self.assertRaises(MarketError):
                candles("BTCUSDT", "24H")


try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QSettings, Qt
    from PySide6.QtWidgets import QApplication
    spec = importlib.util.spec_from_file_location("kernova_crypto_main", APP / "main.py")
    crypto = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(crypto)
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is unavailable")
class CryptoWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.window = crypto.Crypto(autostart=False)
        self.window.cache = Path(self.temp.name) / "markets.json"
        self.window.settings = QSettings(str(Path(self.temp.name) / "preferences.ini"), QSettings.Format.IniFormat)
        self.window.watchlist.clear()
        self.rows = [Ticker("BTCUSDT", "BTC", 100, -2, 1000, 110, 90, 1000),
                     Ticker("ETHUSDT", "ETH", 9, 1, 900, 10, 8, 1000)]

    def tearDown(self):
        self.window.close()
        self.temp.cleanup()

    def test_prices_sort_numerically_and_watchlist_survives_refresh(self):
        self.window.received("prices", self.rows, None)
        self.window.proxy.sort(2, Qt.SortOrder.AscendingOrder)
        index = self.window.proxy.mapToSource(self.window.proxy.index(0, 1))
        self.assertEqual(self.window.model.rows[index.row()].symbol, "ETHUSDT")
        self.window.model.setData(self.window.model.index(0, 0), Qt.CheckState.Checked.value, Qt.ItemDataRole.CheckStateRole)
        self.assertIn("BTCUSDT", self.window.settings.value("watchlist"))
        self.window.received("prices", list(reversed(self.rows)), None)
        self.assertIn("BTCUSDT", self.window.watchlist)
        self.window.change_scope(1)
        self.assertEqual(self.window.proxy.rowCount(), 1)

    def test_old_chart_response_cannot_replace_selected_market(self):
        self.window.active_symbol = "ETHUSDT"
        self.window.received("chart:BTCUSDT:24H", [(1000, 10, 12, 8, 11, 5)], None)
        self.assertEqual(self.window.chart.rows, [])

    def test_featured_market_opens_when_hidden_by_search(self):
        self.window.received("prices", self.rows, None)
        self.window.search.setText("BTC")
        with patch.object(self.window, "fetch_chart"):
            self.window.open_symbol("ETHUSDT")
        self.assertEqual(self.window.active_symbol, "ETHUSDT")
        self.assertEqual(self.window.search.text(), "")
        self.assertEqual(self.window.model.rows[
            self.window.proxy.mapToSource(self.window.table.currentIndex()).row()].symbol, "ETHUSDT")
        self.assertFalse(crypto.coin_icon("BTC").isNull())
        self.assertFalse(crypto.coin_icon("UNLISTED").isNull())

    def test_sort_shortcut_returns_to_all_markets_for_custom_sort(self):
        self.window.received("prices", self.rows, None)
        self.window.scope.setCurrentIndex(2)
        self.assertEqual(self.window.table.horizontalHeader().sortIndicatorSection(), 3)
        self.window.table.sortByColumn(2, Qt.SortOrder.AscendingOrder)
        self.assertEqual(self.window.scope.currentIndex(), 0)

    def test_closing_window_suppresses_late_network_delivery(self):
        delivered = []
        task = crypto.Fetch("prices", lambda: self.rows, self.window.stopping)
        task.signals.finished.connect(lambda *args: delivered.append(args))
        self.window.close()
        task.run()
        self.assertEqual(delivered, [])

    def test_rate_limit_keeps_snapshot_and_stops_requests(self):
        self.window.received("prices", self.rows, None)
        self.window.received("prices", None, MarketError("Provider requested a pause.", 120))
        self.assertEqual(self.window.model.rows, self.rows)
        with patch.object(crypto.QThreadPool, "globalInstance") as pool:
            self.window.refresh_all()
            pool.assert_not_called()

    def test_offline_snapshot_round_trip_and_invalid_data(self):
        self.window.received("prices", self.rows, None)
        self.window.model.rows = []
        self.window.load_cache()
        self.assertEqual(self.window.model.rows, self.rows)
        self.assertIn("Saved snapshot", self.window.connection.text())
        self.window.model.rows = []
        data = json.loads(self.window.cache.read_text())
        data["rows"][0]["price"] = float("nan")
        self.window.cache.write_text(json.dumps(data))
        self.window.load_cache()
        self.assertEqual(self.window.model.rows, [])


if __name__ == "__main__":
    unittest.main()
