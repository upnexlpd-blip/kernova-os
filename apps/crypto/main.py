#!/usr/bin/python3
"""Kernova Crypto, a native public-market explorer."""
from dataclasses import asdict
from datetime import datetime, timezone
from functools import lru_cache
import json
import math
import os
import re
from pathlib import Path
import sys
import tempfile
from threading import Event
import time

from PySide6.QtCore import (QAbstractTableModel, QModelIndex, QObject, QPointF, QRectF,
                            QRunnable, QSettings, QSortFilterProxyModel, QStandardPaths,
                            Qt, QSize, QThreadPool, QTimer, Signal)
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QComboBox,
                               QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QMainWindow, QPushButton, QSplitter, QTableView,
                               QVBoxLayout, QWidget, QScrollArea)
from market_data import MarketError, PERIODS, Ticker, candles, exchange_symbols, parse_tickers, price, request_json


@lru_cache(maxsize=512)
def coin_icon(symbol):
    name = symbol.lower() if re.fullmatch(r"[A-Za-z0-9-]{1,30}", symbol) else "generic"
    path = Path(__file__).with_name("icons") / (name + ".png")
    if path.is_file() and name != "generic":
        icon = QIcon(str(path))
        icon.addFile(str(path), QSize(), QIcon.Mode.Selected)
        return icon
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#34364e"))
    painter.drawEllipse(2, 2, 124, 124)
    painter.setPen(QColor("#d7cef4"))
    font = painter.font()
    font.setPixelSize(43)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, symbol[:2].upper())
    painter.end()
    return QIcon(pixmap)


class AssetCard(QPushButton):
    def __init__(self, symbol, name):
        super().__init__()
        self.symbol = symbol
        self.setObjectName("assetCard")
        self.setMinimumHeight(106)
        self.setAccessibleName("View " + name + " market")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(7)
        heading = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(coin_icon(symbol.removesuffix("USDT")).pixmap(30, 30))
        heading.addWidget(logo)
        heading.addWidget(QLabel(name), 1)
        self.change = QLabel("Loading")
        heading.addWidget(self.change)
        layout.addLayout(heading)
        self.value = QLabel("Waiting for price")
        self.value.setObjectName("cardValue")
        layout.addWidget(self.value)
        for label in self.findChildren(QLabel):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            label.setTextFormat(Qt.TextFormat.PlainText)

    def update_price(self, row):
        self.value.setText(price(row.price) + " USDT")
        self.change.setText(f"{row.change:+.2f}%")
        self.setAccessibleDescription(f"{price(row.price)} USDT. 24-hour change {row.change:+.2f} percent.")
        self.change.setStyleSheet("color: " + ("#72e3bb" if row.change >= 0 else "#ff9aa9"))


class Signals(QObject):
    finished = Signal(str, object, object)


class Fetch(QRunnable):
    def __init__(self, key, function, stopping):
        super().__init__()
        self.key, self.function = key, function
        self.stopping = stopping
        self.signals = Signals()

    def run(self):
        try:
            value, error = self.function(), None
        except Exception as reason:
            value, error = None, reason
        if not self.stopping.is_set():
            try:
                self.signals.finished.emit(self.key, value, error)
            except RuntimeError:
                if not self.stopping.is_set():
                    raise


class Markets(QAbstractTableModel):
    headers = ("Watch", "Market", "Price · USDT", "24h change", "24h volume")

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
        if role == Qt.ItemDataRole.DecorationRole and column == 1:
            return coin_icon(row.base)
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
        self.hover = None
        self.setMouseTracking(True)
        self.setMinimumSize(280, 180)
        self.setAccessibleName("OHLC price chart in USDT")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#a8aec6"))
        if not self.rows:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.message)
            return
        area = QRectF(12, 24, max(1, self.width() - 100), max(1, self.height() - 94))
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
        peak_volume = max(max(row[5] for row in self.rows), 1)
        for index, row in enumerate(self.rows):
            _, open_, peak, trough, close, _ = row
            color = QColor("#65d8b9" if close >= open_ else "#f58ba3")
            x = area.left() + (index + .5) * width
            painter.setPen(QPen(color, 1))
            painter.drawLine(QPointF(x, y(peak)), QPointF(x, y(trough)))
            painter.fillRect(QRectF(x - width * .32, min(y(open_), y(close)),
                                   max(1, width * .64), max(1, abs(y(close) - y(open_)))), color)
            volume_height = row[5] / peak_volume * 26
            color.setAlpha(105)
            painter.fillRect(QRectF(x - width * .32, area.bottom() + 34 - volume_height,
                                   max(1, width * .64), volume_height), color)
        if self.hover is not None and self.hover < len(self.rows):
            x = area.left() + (self.hover + .5) * width
            painter.setPen(QPen(QColor("#bcb7e7"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(x, area.top()), QPointF(x, area.bottom() + 34))
        painter.setPen(QColor("#a8aec6"))
        for index, alignment in ((0, Qt.AlignmentFlag.AlignLeft), (-1, Qt.AlignmentFlag.AlignRight)):
            label = datetime.fromtimestamp(self.rows[index][0] / 1000, timezone.utc).strftime("%d %b %H:%M UTC")
            painter.drawText(QRectF(area.left(), area.bottom() + 43, area.width(), 24), alignment, label)

    def mouseMoveEvent(self, event):
        if self.rows:
            position = (event.position().x() - 12) / max(1, self.width() - 100)
            self.hover = max(0, min(len(self.rows) - 1, int(position * len(self.rows))))
            row = self.rows[self.hover]
            stamp = datetime.fromtimestamp(row[0] / 1000, timezone.utc).strftime("%d %b %H:%M UTC")
            self.setToolTip(f"{stamp}\nOpen {price(row[1])} · High {price(row[2])}\n"
                            f"Low {price(row[3])} · Close {price(row[4])}\nBase-asset volume {row[5]:,.2f}")
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.hover = None
        self.update()
        super().leaveEvent(event)


class Crypto(QMainWindow):
    def __init__(self, autostart=True):
        super().__init__()
        self.setWindowTitle("Kernova Crypto")
        icon = Path("/usr/share/icons/hicolor/scalable/apps/kernova-logo.svg")
        if not icon.is_file():
            icon = Path(__file__).resolve().parents[2] / "branding/kernova-logo.svg"
        self.setWindowIcon(QIcon(str(icon)))
        self.resize(1180, 790)
        self.setMinimumSize(680, 480)
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
        self.stopping = Event()
        self.cooldown = 0
        self.chart_at = 0
        self.cache = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)) / "markets.json"

        root = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(root)
        self.setCentralWidget(scroll)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(26, 22, 26, 18)
        layout.setSpacing(16)
        title = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(self.windowIcon().pixmap(34, 34))
        title.addWidget(logo)
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
        self.featured = QGridLayout()
        self.featured.setSpacing(12)
        self.featured_columns = 4
        self.asset_cards = []
        for symbol, name in (("BTCUSDT", "Bitcoin"), ("ETHUSDT", "Ethereum"),
                             ("SOLUSDT", "Solana"), ("BNBUSDT", "BNB")):
            card = AssetCard(symbol, name)
            card.clicked.connect(lambda checked=False, value=symbol: self.open_symbol(value))
            self.asset_cards.append(card)
            self.featured.addWidget(card, 0, len(self.asset_cards) - 1)
        layout.addLayout(self.featured)
        self.market_summary = QLabel("Market overview is loading…")
        self.market_summary.setWordWrap(True)
        layout.addWidget(self.market_summary)

        split = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(split, 1)
        detail = QFrame()
        detail.setObjectName("detail")
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(20, 16, 20, 12)
        heading = QHBoxLayout()
        self.pair_icon = QLabel()
        self.pair_icon.setPixmap(coin_icon("BTC").pixmap(38, 38))
        heading.addWidget(self.pair_icon)
        self.pair = QLabel("BTC / USDT")
        self.pair.setObjectName("pair")
        heading.addWidget(self.pair)
        heading.addStretch()
        detail_layout.addLayout(heading)
        periods = QHBoxLayout()
        periods.addStretch()
        self.periods = QButtonGroup(self)
        for index, period in enumerate(PERIODS):
            button = QPushButton(period)
            button.setCheckable(True)
            button.setChecked(index == 0)
            self.periods.addButton(button)
            button.clicked.connect(lambda checked, value=period: self.change_period(value))
            periods.addWidget(button)
        detail_layout.addLayout(periods)
        self.selected_price = QLabel("Waiting for price")
        self.selected_price.setObjectName("selectedPrice")
        detail_layout.addWidget(self.selected_price)
        self.summary = QLabel("Waiting for a current price")
        self.summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.summary.setWordWrap(True)
        self.summary.setObjectName("summary")
        detail_layout.addWidget(self.summary)
        self.chart = Chart()
        detail_layout.addWidget(self.chart, 1)
        self.chart_status = QLabel("Chart updates every minute. The latest candle can still change.")
        self.chart_status.setWordWrap(True)
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
        self.scope.addItems(["All markets", "Watchlist", "Top gainers", "Top volume"])
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
        self.table.horizontalHeader().sortIndicatorChanged.connect(self.sync_scope_sort)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setIconSize(QSize(26, 26))
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.selectionModel().currentRowChanged.connect(self.select_market)
        self.model.dataChanged.connect(self.save_watchlist)
        self.search.textChanged.connect(self.proxy.setFilterFixedString)
        self.scope.currentIndexChanged.connect(self.change_scope)
        market_layout.addWidget(self.table)
        split.addWidget(market_panel)
        split.insertWidget(0, market_panel)
        split.setSizes([610, 510])
        self.notice = QLabel("Public market prices. Data is supplied by Binance and may be delayed.")
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        for text in (self.pair, self.summary, self.connection, self.chart_status, self.notice, self.market_summary, self.selected_price):
            text.setTextFormat(Qt.TextFormat.PlainText)
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #10131f; color: #e9edf7; font-size: 13px; }
            QLabel { background: transparent; }
            QLabel#brand { font-size: 25px; color: #f2edff; }
            QLabel#pair { font-size: 20px; font-weight: 600; }
            QLabel#summary { font-size: 13px; color: #aeb8cf; }
            QLabel#selectedPrice { font-size: 34px; font-weight: 600; color: #f0edff; }
            QLabel#cardValue { font-size: 19px; font-weight: 600; color: #f0edff; }
            QPushButton#assetCard { background: #1b2032; border: 1px solid #3c405b; border-radius: 12px; text-align: left; }
            QPushButton#assetCard:hover { background: #282b44; border-color: #a190d9; }
            QFrame#detail { background: #191e30; border: 1px solid #414660; border-radius: 14px; }
            QLineEdit, QComboBox { background: #1d2333; border: 1px solid #58627e; border-radius: 6px; padding: 8px; }
            QPushButton { background: #282e43; border: 1px solid #58627e; border-radius: 6px; padding: 8px 14px; }
            QPushButton:hover { background: #3c4260; }
            QPushButton:checked { background: #cabbf6; color: #201e2e; }
            QPushButton:disabled { color: #8891a9; }
            QTableView { background: #161b2a; alternate-background-color: #1b2030; border: 1px solid #394156; border-radius: 8px; selection-background-color: #3b3659; }
            QHeaderView::section { background: #232a3d; color: #bfc8df; border: 0; padding: 10px 6px; }
            QLineEdit:focus, QPushButton:focus, QComboBox:focus { border: 2px solid #c8b6ff; }
            QSplitter::handle { background: #3a4157; height: 5px; }
        """)
        self.load_cache()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        QApplication.instance().aboutToQuit.connect(self.shutdown)
        if autostart:
            self.timer.start(15000)
            QTimer.singleShot(0, self.refresh_all)

    def fetch(self, key, function):
        if key in self.pending or time.monotonic() < self.cooldown:
            return
        if self.stopping.is_set():
            return
        task = Fetch(key, function, self.stopping)
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
            self.update_overview()
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

    def shutdown(self):
        self.stopping.set()
        self.timer.stop()

    def closeEvent(self, event):
        self.shutdown()
        super().closeEvent(event)

    def update_summary(self):
        row = next((row for row in self.model.rows if row.symbol == self.active_symbol), None)
        if row:
            self.pair.setText(row.base + " / USDT")
            self.pair_icon.setPixmap(coin_icon(row.base).pixmap(38, 38))
            self.selected_price.setText(price(row.price) + " USDT")
            self.summary.setText(f"{row.change:+.2f}% in 24h\nHigh {price(row.high)} · Low {price(row.low)}\n"
                                 f"24h volume {row.volume:,.0f} USDT")

    def update_overview(self):
        by_symbol = {row.symbol: row for row in self.model.rows}
        for card in self.asset_cards:
            row = by_symbol.get(card.symbol)
            card.setEnabled(row is not None)
            if row is not None:
                card.update_price(row)
            else:
                card.value.setText("Market unavailable")
                card.change.setText("Unavailable")
        rising = sum(row.change > 0 for row in self.model.rows)
        falling = sum(row.change < 0 for row in self.model.rows)
        unchanged = len(self.model.rows) - rising - falling
        volume = sum(row.volume for row in self.model.rows)
        self.market_summary.setText(f"{len(self.model.rows)} markets   ·   {rising} advancing   ·   "
                                    f"{falling} declining   ·   {unchanged} unchanged   ·   "
                                    f"USDT spot volume {volume:,.0f} in 24h")

    def open_symbol(self, symbol):
        row_index = next((index for index, row in enumerate(self.model.rows) if row.symbol == symbol), None)
        if row_index is None:
            return
        index = self.proxy.mapFromSource(self.model.index(row_index, 1))
        if not index.isValid():
            self.search.clear()
            self.scope.setCurrentIndex(0)
            index = self.proxy.mapFromSource(self.model.index(row_index, 1))
        if index.isValid():
            self.table.selectRow(index.row())
            self.select_market(index)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not hasattr(self, "featured"):
            return
        columns = 4 if self.width() >= 1000 else 2
        if columns != self.featured_columns:
            self.featured_columns = columns
            for index, card in enumerate(self.asset_cards):
                self.featured.removeWidget(card)
                self.featured.addWidget(card, index // columns, index % columns)

    def sync_scope_sort(self, column, order):
        scope = self.scope.currentIndex()
        expected = 3 if scope == 2 else 4
        if scope >= 2 and (column != expected or order != Qt.SortOrder.DescendingOrder):
            self.scope.setCurrentIndex(0)

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
        if index in (2, 3):
            self.table.sortByColumn(3 if index == 2 else 4, Qt.SortOrder.DescendingOrder)

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
            self.update_overview()
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
    screen = app.primaryScreen()
    if screen is not None:
        available = screen.availableGeometry()
        window.resize(min(window.width(), available.width() - 32),
                      min(window.height(), available.height() - 32))
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
