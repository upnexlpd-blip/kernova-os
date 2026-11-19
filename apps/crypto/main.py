#!/usr/bin/python3
"""Kernova Crypto, a native public-market explorer."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time

from PySide6.QtCore import (QAbstractTableModel, QModelIndex, QObject, QPointF, QRectF,
                            QRunnable, QSettings, QSortFilterProxyModel, QStandardPaths,
                            Qt, QThreadPool, QTimer, Signal)
from PySide6.QtGui import QColor, QIcon, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QComboBox,
                               QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QMainWindow, QPushButton, QSplitter, QTableView,
                               QVBoxLayout, QWidget)
from market_data import MarketError, PERIODS, Ticker, candles, exchange_symbols, parse_tickers, price, request_json


class Signals(QObject):
    finished = Signal(str, object, object)


class Fetch(QRunnable):
    def __init__(self, key, function):
        super().__init__()
        self.key, self.function = key, function
        self.signals = Signals()

    def run(self):
        try:
            value, error = self.function(), None
        except Exception as reason:
            value, error = None, reason
        self.signals.finished.emit(self.key, value, error)


class Markets(QAbstractTableModel):
    headers = ("Watch", "Market", "Price · USDT", "24h change", "24h volume · USDT")

    def __init__(self, watchlist, parent=None):
        super().__init__(parent)
        self.rows = []
        self.watchlist = watchlist

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self.rows[index.row()]
        column = index.column()
        if role == Qt.ItemDataRole.CheckStateRole and column == 0:
            return Qt.CheckState.Checked if row.symbol in self.watchlist else Qt.CheckState.Unchecked
        if role == Qt.ItemDataRole.UserRole:
            return (row.symbol in self.watchlist, row.base, row.price, row.change, row.volume)[column]
        if role == Qt.ItemDataRole.DisplayRole:
            return ("", row.base + " / USDT", price(row.price), f"{row.change:+.2f}%", f"{row.volume:,.0f}")[column]
        if role == Qt.ItemDataRole.ForegroundRole and column == 3:
            return QColor("#67dec1" if row.change >= 0 else "#ff99a9")
        if role == Qt.ItemDataRole.TextAlignmentRole and column >= 2:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

    def flags(self, index):
        result = super().flags(index)
        if index.column() == 0:
            result |= Qt.ItemFlag.ItemIsUserCheckable
        return result

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.CheckStateRole or index.column() != 0:
            return False
        symbol = self.rows[index.row()].symbol
        if value == Qt.CheckState.Checked.value:
            self.watchlist.add(symbol)
        else:
            self.watchlist.discard(symbol)
        self.dataChanged.emit(index, index)
        return True


class Filter(QSortFilterProxyModel):
    watched = False

    def filterAcceptsRow(self, row, parent):
        ticker = self.sourceModel().rows[row]
        return (not self.watched or ticker.symbol in self.sourceModel().watchlist) and super().filterAcceptsRow(row, parent)


class Chart(QWidget):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.message = "Select a market to load its chart."
        self.setMinimumSize(280, 230)
        self.setAccessibleName("OHLC price chart in USDT")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#a8aec6"))
        if not self.rows:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.message)
            return
        area = QRectF(12, 18, max(1, self.width() - 100), max(1, self.height() - 56))
        low = min(row[3] for row in self.rows)
        high = max(row[2] for row in self.rows)
        spread = max(high - low, high * .001)
        low -= spread * .06
        high += spread * .06

        def y(value):
            return area.bottom() - (value - low) / (high - low) * area.height()

        for step in range(5):
            value = low + (high - low) * step / 4
            position = y(value)
            painter.setPen(QPen(QColor("#30374b"), 1))
            painter.drawLine(QPointF(area.left(), position), QPointF(area.right(), position))
            painter.setPen(QColor("#a8aec6"))
            painter.drawText(QRectF(area.right() + 8, position - 9, 80, 20), Qt.AlignmentFlag.AlignVCenter, price(value))
        width = area.width() / len(self.rows)
        for index, row in enumerate(self.rows):
            _, open_, peak, trough, close, _ = row
            color = QColor("#65d8b9" if close >= open_ else "#f58ba3")
            x = area.left() + (index + .5) * width
            painter.setPen(QPen(color, 1))
            painter.drawLine(QPointF(x, y(peak)), QPointF(x, y(trough)))
            painter.fillRect(QRectF(x - width * .32, min(y(open_), y(close)),
                                   max(1, width * .64), max(1, abs(y(close) - y(open_)))), color)
        painter.setPen(QColor("#a8aec6"))
        for index, alignment in ((0, Qt.AlignmentFlag.AlignLeft), (-1, Qt.AlignmentFlag.AlignRight)):
            label = datetime.fromtimestamp(self.rows[index][0] / 1000, timezone.utc).strftime("%d %b %H:%M UTC")
            painter.drawText(QRectF(area.left(), area.bottom() + 12, area.width(), 24), alignment, label)


class Crypto(QMainWindow):
    def __init__(self, autostart=True):
        super().__init__()
        self.setWindowTitle("Kernova Crypto")
        icon = Path("/usr/share/icons/hicolor/scalable/apps/kernova-logo.svg")
        if not icon.is_file():
            icon = Path(__file__).resolve().parents[2] / "branding/kernova-logo.svg"
        self.setWindowIcon(QIcon(str(icon)))
        self.resize(1180, 790)
        self.setMinimumSize(760, 600)
        self.settings = QSettings("KERNOVA", "Crypto")
        saved = self.settings.value("watchlist", ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
        self.watchlist = {symbol for symbol in (saved if isinstance(saved, list) else [saved])
                          if isinstance(symbol, str)}
        self.symbols = {}
        self.symbols_at = 0
        self.snapshot_at = 0
        self.active_symbol = "BTCUSDT"
        self.period = "24H"
        self.pending = {}
        self.cooldown = 0
        self.chart_at = 0
        self.cache = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)) / "markets.json"

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(26, 22, 26, 18)
        layout.setSpacing(16)
        title = QHBoxLayout()
        brand = QLabel("Kernova <b>Crypto</b>")
        brand.setObjectName("brand")
        title.addWidget(brand)
        title.addStretch()
        self.connection = QLabel("Connecting to market data…")
        title.addWidget(self.connection)
        self.refresh = QPushButton("Refresh")
        self.refresh.clicked.connect(self.refresh_all)
        title.addWidget(self.refresh)
        layout.addLayout(title)
        self.caption = QLabel("Binance Spot · USDT markets · Prices refresh every 15 seconds")
        layout.addWidget(self.caption)

        split = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(split, 1)
        detail = QFrame()
        detail.setObjectName("detail")
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(20, 16, 20, 12)
        heading = QHBoxLayout()
        self.pair = QLabel("BTC / USDT")
        self.pair.setObjectName("pair")
        heading.addWidget(self.pair)
        heading.addStretch()
        self.periods = QButtonGroup(self)
        for index, period in enumerate(PERIODS):
            button = QPushButton(period)
            button.setCheckable(True)
            button.setChecked(index == 0)
            self.periods.addButton(button)
            button.clicked.connect(lambda checked, value=period: self.change_period(value))
            heading.addWidget(button)
        detail_layout.addLayout(heading)
        self.summary = QLabel("Waiting for a current price")
        self.summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.summary.setWordWrap(True)
        self.summary.setObjectName("summary")
        detail_layout.addWidget(self.summary)
        self.chart = Chart()
        detail_layout.addWidget(self.chart, 1)
        self.chart_status = QLabel("Chart updates every minute. The latest candle can still change.")
        detail_layout.addWidget(self.chart_status)
        split.addWidget(detail)

        market_panel = QWidget()
        market_layout = QVBoxLayout(market_panel)
        market_layout.setContentsMargins(0, 0, 0, 0)
        tools = QHBoxLayout()
        search_label = QLabel("Find a market")
        self.search = QLineEdit()
        self.search.setPlaceholderText("BTC, ETH, SOL…")
        self.search.setClearButtonEnabled(True)
        search_label.setBuddy(self.search)
        tools.addWidget(search_label)
        tools.addWidget(self.search, 1)
        self.scope = QComboBox()
        self.scope.setAccessibleName("Market list")
        self.scope.addItems(["All markets", "Watchlist"])
        tools.addWidget(self.scope)
        market_layout.addLayout(tools)
        self.model = Markets(self.watchlist, self)
        self.proxy = Filter(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortRole(Qt.ItemDataRole.UserRole)
        self.proxy.setFilterKeyColumn(1)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.table = QTableView()
        self.table.setAccessibleName("Spot cryptocurrency prices")
        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(4, Qt.SortOrder.DescendingOrder)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.selectionModel().currentRowChanged.connect(self.select_market)
        self.model.dataChanged.connect(self.save_watchlist)
        self.search.textChanged.connect(self.proxy.setFilterFixedString)
        self.scope.currentIndexChanged.connect(self.change_scope)
        market_layout.addWidget(self.table)
        split.addWidget(market_panel)
        split.setSizes([390, 300])
        self.notice = QLabel("Public market prices. Data is supplied by Binance and may be delayed.")
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        for text in (self.pair, self.summary, self.connection, self.chart_status, self.notice):
            text.setTextFormat(Qt.TextFormat.PlainText)
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #121622; color: #e9edf7; font-size: 13px; }
            QLabel { background: transparent; }
            QLabel#brand { font-size: 25px; color: #f2edff; }
            QLabel#pair { font-size: 20px; font-weight: 600; }
            QLabel#summary { font-size: 17px; color: #e3def4; }
            QFrame#detail { background: #1b2131; border: 1px solid #394156; border-radius: 12px; }
            QLineEdit, QComboBox { background: #1d2333; border: 1px solid #58627e; border-radius: 6px; padding: 8px; }
            QPushButton { background: #282e43; border: 1px solid #58627e; border-radius: 6px; padding: 8px 14px; }
            QPushButton:hover { background: #3c4260; }
            QPushButton:checked { background: #cabbf6; color: #201e2e; }
            QPushButton:disabled { color: #8891a9; }
            QTableView { background: #151a28; alternate-background-color: #1b2131; gridline-color: #30394e; border: 1px solid #394156; selection-background-color: #343451; }
            QHeaderView::section { background: #232a3d; color: #bfc8df; border: 0; padding: 10px 6px; }
            QLineEdit:focus, QPushButton:focus, QComboBox:focus { border: 2px solid #c8b6ff; }
            QSplitter::handle { background: #3a4157; height: 5px; }
        """)
        self.load_cache()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        if autostart:
            self.timer.start(15000)
            QTimer.singleShot(0, self.refresh_all)

    def fetch(self, key, function):
        if key in self.pending or time.monotonic() < self.cooldown:
            return
        task = Fetch(key, function)
        self.pending[key] = task
        task.signals.finished.connect(self.received)
        QThreadPool.globalInstance().start(task)

    def refresh_all(self):
        if time.monotonic() < self.cooldown:
            return
        if not self.symbols or time.monotonic() - self.symbols_at > 3600:
            self.fetch("symbols", exchange_symbols)
        else:
            self.fetch("prices", lambda: parse_tickers(request_json("ticker/24hr"), self.symbols))
        self.fetch_chart()

    def fetch_chart(self):
        if self.chart.rows and time.time() - self.chart_at < 60:
            return
        symbol, period = self.active_symbol, self.period
        self.fetch("chart:" + symbol + ":" + period, lambda: candles(symbol, period))

    def received(self, key, value, error):
        self.pending.pop(key, None)
        if error is not None:
            if isinstance(error, MarketError):
                self.cooldown = max(self.cooldown, time.monotonic() + error.retry_after)
            message = str(error) if isinstance(error, MarketError) else "Market data could not be updated."
            if key.startswith("chart:"):
                if key == "chart:" + self.active_symbol + ":" + self.period:
                    self.chart_status.setText(message + " Displayed chart may be out of date.")
            else:
                self.connection.setText("Connection interrupted")
                self.notice.setText(message + " The previous snapshot is retained.")
            return
        if key == "symbols":
            self.symbols, self.symbols_at = value, time.monotonic()
            self.refresh_all()
        elif key == "prices":
            self.model.beginResetModel()
            self.model.rows = value
            self.model.endResetModel()
            for index, row in enumerate(self.model.rows):
                if row.symbol == self.active_symbol:
                    mapped = self.proxy.mapFromSource(self.model.index(index, 1))
                    if mapped.isValid():
                        self.table.selectRow(mapped.row())
                    break
            self.snapshot_at = time.time()
            market_time = max(row.at for row in value) / 1000
            delayed = time.time() - market_time > 120
            self.connection.setText("Provider snapshot delayed" if delayed else "Updated " + datetime.now().strftime("%H:%M:%S"))
            source_time = datetime.fromtimestamp(market_time, timezone.utc).strftime("%d %b %H:%M:%S UTC")
            self.notice.setText(f"{len(value)} active USDT markets · Binance Spot · Market timestamp {source_time}")
            self.update_summary()
            self.save_cache()
        elif key == "chart:" + self.active_symbol + ":" + self.period:
            self.chart.rows = value
            self.chart.update()
            self.chart_at = time.time()
            interval = PERIODS[self.period][0]
            self.chart_status.setText(f"{interval} candles · Updated {datetime.now():%H:%M:%S} · Latest candle can still change")

    def tick(self):
        if self.snapshot_at and time.time() - self.snapshot_at > 60:
            self.connection.setText("Previous snapshot · waiting for an update")
        self.refresh_all()

    def update_summary(self):
        row = next((row for row in self.model.rows if row.symbol == self.active_symbol), None)
        if row:
            self.pair.setText(row.base + " / USDT")
            self.summary.setText(f"{price(row.price)} USDT   {row.change:+.2f}% in 24h\n"
                                 f"24h high {price(row.high)}   Low {price(row.low)}   Volume {row.volume:,.0f} USDT")

    def select_market(self, index, previous=QModelIndex()):
        if not index.isValid():
            return
        symbol = self.model.rows[self.proxy.mapToSource(index).row()].symbol
        if symbol == self.active_symbol:
            return
        self.active_symbol = symbol
        self.chart_at = 0
        self.chart.rows = []
        self.chart.message = "Loading chart…"
        self.chart.update()
        self.update_summary()
        self.fetch_chart()

    def change_period(self, period):
        self.period = period
        self.chart_at = 0
        self.chart.rows = []
        self.chart.message = "Loading chart…"
        self.chart.update()
        self.fetch_chart()

    def change_scope(self, index):
        self.proxy.watched = index == 1
        self.proxy.invalidateFilter()

    def save_watchlist(self, *args):
        self.settings.setValue("watchlist", sorted(self.watchlist))
        self.proxy.invalidateFilter()

    def save_cache(self):
        temporary = None
        try:
            self.cache.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(dir=self.cache.parent, prefix=".markets-")
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump({"at": self.snapshot_at, "rows": [asdict(row) for row in self.model.rows]}, stream)
            os.replace(temporary, self.cache)
        except OSError:
            self.notice.setText("Prices updated. The local offline snapshot could not be saved.")
        finally:
            if temporary and Path(temporary).exists():
                Path(temporary).unlink()

    def load_cache(self):
        try:
            data = json.loads(self.cache.read_text(encoding="utf-8"))
            rows = [Ticker(**row) for row in data["rows"]]
            at = float(data["at"])
            if not math.isfinite(at) or not 0 < at <= time.time() + 60 or not rows:
                raise ValueError("Invalid snapshot timestamp")
            for row in rows:
                if not isinstance(row.symbol, str) or not isinstance(row.base, str) or not row.base:
                    raise ValueError("Invalid snapshot market")
                if not all(math.isfinite(value) for value in (row.price, row.change, row.volume, row.high, row.low)):
                    raise ValueError("Invalid snapshot value")
                if not (row.price > 0 and row.volume >= 0 and row.high >= row.low > 0):
                    raise ValueError("Invalid snapshot range")
            self.snapshot_at = at
            self.model.beginResetModel()
            self.model.rows = rows
            self.model.endResetModel()
            self.update_summary()
            self.connection.setText("Saved snapshot · checking current prices")
        except (OSError, ValueError, KeyError, TypeError):
            pass


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("KERNOVA")
    app.setApplicationName("kernova-crypto")
    app.setApplicationDisplayName("Kernova Crypto")
    app.setDesktopFileName("org.kernova.Crypto")
    window = Crypto()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
