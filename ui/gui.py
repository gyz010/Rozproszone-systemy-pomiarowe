import time
import json
import sys
from collections import deque
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, 
    QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import pyqtgraph as pg
import numpy as np


from connection import ConnectionWindow, RestInterface


class MainGui(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.nam = QNetworkAccessManager()
        self.setWindowTitle("Main Application")
        self.setFixedSize(800, 600)
        self._init_ui()

        self._data_points = np.array([])

    def _init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.connection_label = QLabel()

        self.device_combo = QComboBox()
        self.device_combo.setEnabled(False)
        self.device_combo.currentTextChanged.connect(self._on_sensor_changed)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Value')
        self.plot_widget.setLabel('bottom', 'Samples')
        self.curve = self.plot_widget.plot(pen=pg.mkPen('g', width=2))
        layout.addWidget(self.plot_widget)


        layout.addWidget(self.connection_label)
        layout.addWidget(self.device_combo)
        layout.addStretch()
        
    def set_url(self, url: QUrl):
        self.rest_interface = RestInterface(self.nam, url)
        self.connection_label.setText(f"Connected to: {url.toString()}")
        self._update_sensor_list() #initial update

    def _update_sensor_list(self):
        self.rest_interface.fetch_devices(callback=self._set_sensor_list)
         
    def _set_sensor_list(self, sensors):
        if sensors is None:
            return
        self.device_combo.clear()
        self.device_combo.addItems(sensors)
        self.device_combo.setEnabled(True)

    def _on_sensor_changed(self):
        self.rest_interface.fetch_sensor_data(
            sensor=self.device_combo.currentText(), 
            callback=self._handle_sensor_data
        )

    def _handle_sensor_data(self, data):
        if data:
            self._data_points = data
            self._populate_graph()

    def _populate_graph(self) -> None:
        if not self._data_points:
            self.plot_widget.clear()
            return

        # Sort ascending (API returns DESC)
        data = sorted(self._data_points, key=lambda x: x["ts_ms"])
        
        x = [d["ts_ms"] for d in data]
        y = [d["value"] for d in data]
        
        unit = self._data_points[0].get("unit", "")
        sensor = self._data_points[0].get("sensor", "Value")

        self.plot_widget.clear()
        plot_item = self.plot_widget.getPlotItem()
        plot_item.setLabel("left", sensor, units=unit)
        plot_item.setLabel("bottom", "Time", units="ms")
        
        self.plot_widget.plot(
            x, y, 
            pen=pg.mkPen(color='c', width=2),
            symbol='o', 
            symbolSize=5, 
            symbolBrush='b'
        )

    


def main() -> None:
    app = QApplication(sys.argv)
    conn_window = ConnectionWindow()
    main_gui = MainGui()

    # Logika przełączania: pokaż MainGui, zamknij ConnectionWindow
    def on_connection_success(url: QUrl):
        main_gui.set_url(url)
        main_gui.show()

    conn_window.connection_success.connect(on_connection_success)
    conn_window.connection_success.connect(conn_window.close)

    conn_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()