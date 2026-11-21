"""Disposable graphical session fixture; launch with QT_QPA_PLATFORM=wayland or xcb."""
import sys
from PySide6.QtWidgets import QApplication, QWidget

app = QApplication(sys.argv)
app.setApplicationName("WindowToolsQA")
windows = []
for name in sys.argv[1:]:
    w = QWidget()
    w.setWindowTitle("WT-QA-" + name)
    w.resize(260, 180)
    if name == "Fixed":
        w.setFixedSize(260, 180)
    w.show()
    windows.append(w)
sys.exit(app.exec())
