import sys
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, 
    QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QSizePolicy,
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

        top_bar = QHBoxLayout()
        self.connection_label = QLabel("Not connected")
        self.health_label = QLabel("Health: -")
        top_bar.addWidget(self.connection_label)
        top_bar.addStretch()
        top_bar.addWidget(self.health_label)
        layout.addLayout(top_bar)

        content = QHBoxLayout()

        left_panel = QVBoxLayout()
        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.setEnabled(False)
        self.device_combo.currentTextChanged.connect(self._on_sensor_changed)
        device_row.addWidget(self.device_combo)
        left_panel.addLayout(device_row)

        self.last_updated_label = QLabel("Last updated: -")
        self.last_updated_label.setStyleSheet("color: gray;")
        left_panel.addWidget(self.last_updated_label)
        left_panel.addStretch()
        content.addLayout(left_panel, stretch=3)

        right_panel = QVBoxLayout()
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Value')
        self.plot_widget.setLabel('bottom', 'Samples')
        self.curve = self.plot_widget.plot(pen=pg.mkPen('g', width=2))
        self._configure_static_plot()
        plot_height = int((600 - 80) * 0.4)
        self.plot_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.plot_widget.setFixedHeight(plot_height)
        right_panel.addWidget(
            self.plot_widget,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
        )
        right_panel.addStretch()
        content.addLayout(right_panel, stretch=2)

        layout.addLayout(content, stretch=1)

        self._health_timer = QTimer(self)
        self._health_timer.setInterval(5000)
        self._health_timer.timeout.connect(self._poll_health)

    def _configure_static_plot(self) -> None:
        plot_item = self.plot_widget.getPlotItem()
        plot_item.setMouseEnabled(x=False, y=False)
        plot_item.hideButtons()
        plot_item.setMenuEnabled(False)
        view_box = plot_item.getViewBox()
        view_box.setMouseEnabled(x=False, y=False)
        view_box.setMenuEnabled(False)
        view_box.wheelEvent = lambda ev, axis=None: ev.ignore()
        
    def set_url(self, url: QUrl):
        self.rest_interface = RestInterface(self.nam, url)
        self.connection_label.setText(f"Connected to: {url.toString()}")
        self._update_sensor_list()
        self._poll_health()
        self._health_timer.start()

    def _poll_health(self) -> None:
        if hasattr(self, "rest_interface"):
            self.rest_interface.fetch_health(callback=self._on_health_result)

    def _on_health_result(self, status: str | None) -> None:
        if status == "ok":
            self.health_label.setText("Health: OK")
            self.health_label.setStyleSheet("color: #2ecc71;")
        elif status is None:
            self.health_label.setText("Health: unreachable")
            self.health_label.setStyleSheet("color: #e74c3c;")
        else:
            self.health_label.setText(f"Health: {status}")
            self.health_label.setStyleSheet("color: #f39c12;")

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
            self.last_updated_label.setText(
                f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

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
        plot_item.autoRange()

    


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