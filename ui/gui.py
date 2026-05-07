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


class ConnectionWindow(QMainWindow):
    connection_success = pyqtSignal(QUrl)

    def __init__(self) -> None:
        super().__init__()
        self.nam = QNetworkAccessManager()
        self.setWindowTitle("Network Client")
        self.setFixedSize(400, 240)
        self._init_ui()



    def _init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Input row
        input_layout = QHBoxLayout()
        title = QLabel("Rozproszone systemy pomiarowe")
    
        layout.addWidget(title)
        
        self.url_input = QLineEdit("http://127.0.0.1:5001")
        self.url_input.setPlaceholderText("http://127.0.0.1:5001")
        self.url_input.setClearButtonEnabled(True)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setFixedWidth(120)
        self.connect_btn.clicked.connect(self._handle_connection)

        input_layout.addWidget(self.url_input)
        input_layout.addWidget(self.connect_btn)

        layout.addLayout(input_layout)
        layout.addStretch()

    def _handle_connection(self) -> None:
        url_str = self.url_input.text().strip()
        if not url_str:
            return

        self.connect_btn.setEnabled(False)
        
        request = QNetworkRequest(QUrl(url_str))
        reply = self.nam.head(request)
        reply.finished.connect(lambda: self._on_check_finished(reply))

    def _on_check_finished(self, reply: QNetworkReply) -> None:
        self.connect_btn.setEnabled(True)
        
        if reply.error() == QNetworkReply.NetworkError.NoError:
            status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            self.url_input.setStyleSheet("border: 1px solid #2ecc71;")
            print(f"Success: HTTP {status_code}")
            url_str = self.url_input.text().strip()
            time.sleep(0.1)
            self.connection_success.emit(QUrl(url_str))
        else:
            self.url_input.setStyleSheet("border: 1px solid #e74c3c;")
            print(f"Connection failed: {reply.errorString()}")
        
        reply.deleteLater()

class MainGui(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.nam = QNetworkAccessManager()
        self.setWindowTitle("Main Application")
        self.setFixedSize(800, 600)
        self._init_ui()

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._fetch_latest_measurement)
        self.max_points = 1000
        self.data_vector = deque(maxlen=self.max_points)

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
        self.url: QUrl = url
        self.connection_label.setText(f"Connected to: {url.toString()}")
        self._fetch_devices()

    def _fetch_devices(self) -> None:
        # Bezpieczne łączenie ścieżek REST
        target_url = self.url.toString().rstrip('/') + "/devices"
        request = QNetworkRequest(QUrl(target_url))
        
        reply = self.nam.get(request)
        reply.finished.connect(lambda r=reply: self._on_devices_fetched(r))

    def _on_devices_fetched(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            raw_data = reply.readAll().data().decode('utf-8')
            try:
                payload = json.loads(raw_data)
                if isinstance(payload, list):
                    sensors = [item.get('sensor') for item in payload if 'sensor' in item]
                    self.device_combo.clear()
                    self.device_combo.addItems(sensors)
                    self.device_combo.setEnabled(True)
            except json.JSONDecodeError:
                print("JSON Parsing error.")
        else:
            print(f"REST API Error: {reply.errorString()}")
            
        reply.deleteLater()
    def _on_sensor_changed(self):
        pass
    def _fetch_latest_measurement(self):
        pass
    
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