import sys
import csv
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QSizePolicy, QDateTimeEdit,
    QSpinBox, QRadioButton, QFileDialog, QFrame,
)
from PyQt6.QtCore import Qt, QUrl, QTimer, QDateTime
from PyQt6.QtNetwork import QNetworkAccessManager
import pyqtgraph as pg

from connection import ConnectionWindow, RestInterface


class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [
            datetime.fromtimestamp(v / 1000).strftime("%H:%M:%S")
            for v in values
        ]


class MainGui(QMainWindow):
    DATA_REFRESH_INTERVAL_MS = 1000
    LIVE_LIMIT = 50

    def __init__(self) -> None:
        super().__init__()
        self.nam = QNetworkAccessManager()
        self.setWindowTitle("Distributed Measurement System")
        self.resize(1100, 680)
        self.setMinimumSize(900, 580)
        self._init_ui()

        self._data_points = []
        self._is_fetching_data = False
        self._is_loading_sensors = False

    def _init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Top bar
        top_bar = QHBoxLayout()
        self.connection_label = QLabel("Not connected")
        self.health_label = QLabel("Health: -")
        top_bar.addWidget(self.connection_label)
        top_bar.addStretch()
        top_bar.addWidget(self.health_label)
        layout.addLayout(top_bar)

        # Main content
        content = QHBoxLayout()
        content.setSpacing(15)

        # === Left panel ===
        left_panel = QVBoxLayout()
        left_panel.setSpacing(6)

        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.setEnabled(False)
        self.device_combo.currentTextChanged.connect(self._on_device_changed)
        device_row.addWidget(self.device_combo)
        left_panel.addLayout(device_row)

        sensor_row = QHBoxLayout()
        sensor_row.addWidget(QLabel("Sensor:"))
        self.sensor_combo = QComboBox()
        self.sensor_combo.setEnabled(False)
        self.sensor_combo.currentTextChanged.connect(self._on_sensor_changed)
        sensor_row.addWidget(self.sensor_combo)
        left_panel.addLayout(sensor_row)

        left_panel.addWidget(self._separator())

        status_heading = QLabel("Sensor Status")
        status_heading.setStyleSheet("font-weight: bold;")
        left_panel.addWidget(status_heading)

        self.online_label = QLabel("● Unknown")
        self.online_label.setStyleSheet("font-weight: bold; color: gray;")
        left_panel.addWidget(self.online_label)

        self.last_seen_label = QLabel("Last seen: -")
        self.uptime_label = QLabel("Session uptime: -")
        self.total_readings_label = QLabel("Total readings: -")
        for lbl in (self.last_seen_label, self.uptime_label, self.total_readings_label):
            lbl.setStyleSheet("color: gray;")
            left_panel.addWidget(lbl)

        left_panel.addWidget(self._separator())

        mode_label = QLabel("View Mode")
        mode_label.setStyleSheet("font-weight: bold;")
        left_panel.addWidget(mode_label)

        self.live_radio = QRadioButton("Live (auto-refresh)")
        self.history_radio = QRadioButton("Historical")
        self.live_radio.setChecked(True)
        self.live_radio.toggled.connect(self._on_mode_changed)
        left_panel.addWidget(self.live_radio)
        left_panel.addWidget(self.history_radio)

        left_panel.addWidget(self._separator())

        range_label = QLabel("Time Range")
        range_label.setStyleSheet("font-weight: bold;")
        left_panel.addWidget(range_label)

        now = QDateTime.currentDateTime()
        one_hour_ago = now.addSecs(-3600)

        from_row = QHBoxLayout()
        from_row.addWidget(QLabel("From:"))
        self.from_dt = QDateTimeEdit(one_hour_ago)
        self.from_dt.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.from_dt.setCalendarPopup(True)
        self.from_dt.setEnabled(False)
        from_row.addWidget(self.from_dt)
        left_panel.addLayout(from_row)

        to_row = QHBoxLayout()
        to_row.addWidget(QLabel("To:"))
        self.to_dt = QDateTimeEdit(now)
        self.to_dt.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.to_dt.setCalendarPopup(True)
        self.to_dt.setEnabled(False)
        to_row.addWidget(self.to_dt)
        left_panel.addLayout(to_row)

        limit_row = QHBoxLayout()
        limit_row.addWidget(QLabel("Max points:"))
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 10000)
        self.limit_spin.setValue(1000)
        self.limit_spin.setEnabled(False)
        limit_row.addWidget(self.limit_spin)
        left_panel.addLayout(limit_row)

        self.load_btn = QPushButton("Load Historical Data")
        self.load_btn.setEnabled(False)
        self.load_btn.clicked.connect(self._load_historical_data)
        left_panel.addWidget(self.load_btn)

        left_panel.addWidget(self._separator())

        stats_label = QLabel("Statistics")
        stats_label.setStyleSheet("font-weight: bold;")
        left_panel.addWidget(stats_label)

        self.stats_count = QLabel("Count: -")
        self.stats_min = QLabel("Min: -")
        self.stats_max = QLabel("Max: -")
        self.stats_avg = QLabel("Avg: -")
        for lbl in (self.stats_count, self.stats_min, self.stats_max, self.stats_avg):
            lbl.setStyleSheet("color: gray;")
            left_panel.addWidget(lbl)

        left_panel.addWidget(self._separator())

        self.last_updated_label = QLabel("Last updated: -")
        self.last_updated_label.setStyleSheet("color: gray;")
        left_panel.addWidget(self.last_updated_label)

        self.export_btn = QPushButton("Export CSV")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export_csv)
        left_panel.addWidget(self.export_btn)

        left_panel.addStretch()
        content.addLayout(left_panel, stretch=2)

        # === Chart ===
        right_panel = QVBoxLayout()
        self.plot_widget = pg.PlotWidget(
            axisItems={"bottom": TimeAxisItem(orientation="bottom")}
        )
        self.plot_widget.setLabel('left', 'Value')
        self.plot_widget.setLabel('bottom', 'Time')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        right_panel.addWidget(self.plot_widget)
        content.addLayout(right_panel, stretch=5)

        layout.addLayout(content, stretch=1)

        self._health_timer = QTimer(self)
        self._health_timer.setInterval(5000)
        self._health_timer.timeout.connect(self._poll_health)

        self._data_timer = QTimer(self)
        self._data_timer.setInterval(self.DATA_REFRESH_INTERVAL_MS)
        self._data_timer.timeout.connect(self._refresh_sensor_data)

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(5000)
        self._status_timer.timeout.connect(self._refresh_status)

    @staticmethod
    def _separator() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    def _on_mode_changed(self, live_checked: bool) -> None:
        is_hist = not live_checked
        self.from_dt.setEnabled(is_hist)
        self.to_dt.setEnabled(is_hist)
        self.limit_spin.setEnabled(is_hist)
        self.load_btn.setEnabled(is_hist and bool(self.sensor_combo.currentText()))
        if live_checked:
            self._data_timer.start()
        else:
            self._data_timer.stop()

    def set_url(self, url: QUrl) -> None:
        self.rest_interface = RestInterface(self.nam, url)
        self.connection_label.setText(f"Connected to: {url.toString()}")
        self._update_sensor_list()
        self._poll_health()
        self._health_timer.start()
        self._data_timer.start()
        self._status_timer.start()

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

    def _update_sensor_list(self) -> None:
        self.rest_interface.fetch_devices(callback=self._set_sensor_list)

    def _set_sensor_list(self, devices) -> None:
        if devices is None:
            return
        self.device_combo.clear()
        self.device_combo.addItems(devices)
        self.device_combo.setEnabled(True)

    def _on_device_changed(self, *_args) -> None:
        self._data_points = []
        self._populate_graph()
        self._clear_stats()
        self._clear_status()
        self.sensor_combo.clear()
        self.sensor_combo.setEnabled(False)
        self.load_btn.setEnabled(False)

        selected_device = self.device_combo.currentText()
        if not selected_device:
            return

        self._is_loading_sensors = True
        self.rest_interface.fetch_sensors(
            device_id=selected_device,
            callback=self._set_device_sensors
        )

    def _set_device_sensors(self, sensors) -> None:
        if sensors is None:
            self._is_loading_sensors = False
            return

        self.sensor_combo.blockSignals(True)
        self.sensor_combo.clear()
        self.sensor_combo.addItems(sensors)
        self.sensor_combo.blockSignals(False)
        self.sensor_combo.setEnabled(bool(sensors))
        self._is_loading_sensors = False
        if self.history_radio.isChecked():
            self.load_btn.setEnabled(bool(sensors))
        self._refresh_sensor_data()
        self._refresh_status()

    def _on_sensor_changed(self, *_args) -> None:
        if self._is_loading_sensors:
            return
        self._data_points = []
        self._populate_graph()
        self._clear_stats()
        self._refresh_sensor_data()
        self._refresh_status()

    def _refresh_sensor_data(self) -> None:
        if not hasattr(self, "rest_interface") or self._is_fetching_data:
            return
        if self.history_radio.isChecked():
            return

        device = self.device_combo.currentText()
        sensor = self.sensor_combo.currentText()
        if not device or not sensor:
            return

        self._is_fetching_data = True
        self.rest_interface.fetch_sensor_data(
            device_id=device,
            sensor=sensor,
            callback=self._handle_sensor_data,
            limit=self.LIVE_LIMIT,
        )

    def _load_historical_data(self) -> None:
        if not hasattr(self, "rest_interface") or self._is_fetching_data:
            return

        device = self.device_combo.currentText()
        sensor = self.sensor_combo.currentText()
        if not device or not sensor:
            return

        from_ts = self.from_dt.dateTime().toMSecsSinceEpoch()
        to_ts = self.to_dt.dateTime().toMSecsSinceEpoch()
        limit = self.limit_spin.value()

        self._is_fetching_data = True
        self.load_btn.setEnabled(False)
        self.rest_interface.fetch_sensor_data(
            device_id=device,
            sensor=sensor,
            callback=self._handle_sensor_data,
            from_ts=from_ts,
            to_ts=to_ts,
            limit=limit,
        )

    def _handle_sensor_data(self, data) -> None:
        self._is_fetching_data = False
        if self.history_radio.isChecked():
            self.load_btn.setEnabled(True)
        if data:
            self._data_points = data
            self._populate_graph()
            self._update_stats()
            self.export_btn.setEnabled(True)
            self.last_updated_label.setText(
                f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

    def _populate_graph(self) -> None:
        self.plot_widget.clear()
        if not self._data_points:
            return

        data = sorted(self._data_points, key=lambda d: d["ts_ms"])
        x = [d["ts_ms"] for d in data]
        y = [d["value"] for d in data]

        unit = self._data_points[0].get("unit", "")
        sensor = self._data_points[0].get("sensor", "Value")

        plot_item = self.plot_widget.getPlotItem()
        plot_item.setLabel("left", sensor, units=unit)
        plot_item.setLabel("bottom", "Time")

        self.plot_widget.plot(
            x, y,
            pen=pg.mkPen(color='c', width=2),
            symbol='o',
            symbolSize=5,
            symbolBrush='b',
        )
        plot_item.autoRange()

    def _update_stats(self) -> None:
        if not self._data_points:
            self._clear_stats()
            return

        values = [d["value"] for d in self._data_points]
        unit = self._data_points[0].get("unit", "")
        u = f" {unit}" if unit else ""

        self.stats_count.setText(f"Count: {len(values)}")
        self.stats_min.setText(f"Min: {min(values):.2f}{u}")
        self.stats_max.setText(f"Max: {max(values):.2f}{u}")
        self.stats_avg.setText(f"Avg: {sum(values) / len(values):.2f}{u}")
        for lbl in (self.stats_count, self.stats_min, self.stats_max, self.stats_avg):
            lbl.setStyleSheet("")

    def _clear_stats(self) -> None:
        for lbl, text in (
            (self.stats_count, "Count: -"),
            (self.stats_min, "Min: -"),
            (self.stats_max, "Max: -"),
            (self.stats_avg, "Avg: -"),
        ):
            lbl.setText(text)
            lbl.setStyleSheet("color: gray;")

    def _refresh_status(self) -> None:
        if not hasattr(self, "rest_interface"):
            return
        device = self.device_combo.currentText()
        sensor = self.sensor_combo.currentText()
        if not device or not sensor:
            return
        self.rest_interface.fetch_sensor_status(device, sensor, self._handle_status)

    def _handle_status(self, data) -> None:
        if data is None:
            self._clear_status()
            return

        if data.get("is_online"):
            self.online_label.setText("● Online")
            self.online_label.setStyleSheet("font-weight: bold; color: #2ecc71;")
        else:
            self.online_label.setText("● Offline")
            self.online_label.setStyleSheet("font-weight: bold; color: #e74c3c;")

        ago_s = data.get("last_seen_ago_s")
        self.last_seen_label.setText(
            f"Last seen: {self._fmt_ago(ago_s)}" if ago_s is not None else "Last seen: -"
        )

        uptime_s = data.get("session_uptime_s")
        self.uptime_label.setText(
            f"Session uptime: {self._fmt_duration(uptime_s)}" if uptime_s is not None else "Session uptime: -"
        )

        count = data.get("total_count")
        self.total_readings_label.setText(
            f"Total readings: {count:,}" if count is not None else "Total readings: -"
        )

        for lbl in (self.last_seen_label, self.uptime_label, self.total_readings_label):
            lbl.setStyleSheet("")

    def _clear_status(self) -> None:
        self.online_label.setText("● Unknown")
        self.online_label.setStyleSheet("font-weight: bold; color: gray;")
        for lbl, text in (
            (self.last_seen_label, "Last seen: -"),
            (self.uptime_label, "Session uptime: -"),
            (self.total_readings_label, "Total readings: -"),
        ):
            lbl.setText(text)
            lbl.setStyleSheet("color: gray;")

    @staticmethod
    def _fmt_ago(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.0f}s ago"
        if seconds < 3600:
            return f"{seconds / 60:.0f}m ago"
        return f"{seconds / 3600:.1f}h ago"

    @staticmethod
    def _fmt_duration(seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        if seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m"

    def _export_csv(self) -> None:
        if not self._data_points:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "measurements.csv", "CSV Files (*.csv)"
        )
        if not path:
            return

        data = sorted(self._data_points, key=lambda d: d["ts_ms"])
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)


def main() -> None:
    app = QApplication(sys.argv)
    conn_window = ConnectionWindow()
    main_gui = MainGui()

    def on_connection_success(url: QUrl):
        main_gui.set_url(url)
        main_gui.show()

    conn_window.connection_success.connect(on_connection_success)
    conn_window.connection_success.connect(conn_window.close)

    conn_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
