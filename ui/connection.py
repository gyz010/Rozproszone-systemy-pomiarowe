import json
import time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, 
    QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel
)
from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


class RestInterface():

    def __init__(self, nam: QNetworkAccessManager, url: QUrl):
        self.url = url
        self.nam = nam
    

    def fetch_devices(self, callback) -> None:
        # Bezpieczne łączenie ścieżek REST
        target_url = self.url.toString().rstrip('/') + "/devices"
        request = QNetworkRequest(QUrl(target_url))
        reply = self.nam.get(request)
        reply.finished.connect(lambda r=reply: self._on_devices_fetched(r, callback))


    def fetch_sensors(self, device_id, callback) -> None:
        target_url = self.url.toString().rstrip('/') + f"/devices/{device_id}/sensors"
        request = QNetworkRequest(QUrl(target_url))
        reply = self.nam.get(request)
        reply.finished.connect(lambda r=reply: self._on_sensors_fetched(r, callback))

    def fetch_sensor_data(self, device_id, sensor, callback, from_ts=None, to_ts=None, limit=20) -> None:
        params = [f"limit={limit}"]
        if from_ts is not None:
            params.append(f"from_ts={from_ts}")
        if to_ts is not None:
            params.append(f"to_ts={to_ts}")
        query = "?" + "&".join(params)
        target_url = self.url.toString().rstrip('/') + f"/measurements/{device_id}/{sensor}{query}"
        request = QNetworkRequest(QUrl(target_url))
        reply = self.nam.get(request)
        reply.finished.connect(lambda r=reply: self._on_sensor_data_fetched(r, callback))

    def fetch_sensor_status(self, device_id, sensor, callback) -> None:
        target_url = self.url.toString().rstrip('/') + f"/devices/{device_id}/sensors/{sensor}/status"
        request = QNetworkRequest(QUrl(target_url))
        reply = self.nam.get(request)
        reply.finished.connect(lambda r=reply: self._on_status_fetched(r, callback))

    def fetch_health(self, callback) -> None:
        target_url = self.url.toString().rstrip('/') + "/health"
        request = QNetworkRequest(QUrl(target_url))
        reply = self.nam.get(request)
        reply.finished.connect(lambda r=reply: self._on_health_fetched(r, callback))

    @staticmethod
    def _on_devices_fetched(reply: QNetworkReply, callback) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            raw_data = reply.readAll().data().decode('utf-8')
            try:
                payload = json.loads(raw_data)
                print(payload)
                if isinstance(payload, list):
                    sensors = [item.get('device_id') for item in payload if 'device_id' in item]
                    callback(sensors)
            except json.JSONDecodeError:
                print("JSON Parsing error.")
        else:
            callback(None)
            print(f"REST API Error: {reply.errorString()}")
            
        reply.deleteLater()

    @staticmethod
    def _on_sensors_fetched(reply: QNetworkReply, callback) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            raw_data = reply.readAll().data().decode('utf-8')
            try:
                payload = json.loads(raw_data)
                if isinstance(payload, list):
                    sensors = [item.get('sensor') for item in payload if 'sensor' in item]
                    callback(sensors)
                else:
                    callback(None)
            except json.JSONDecodeError:
                callback(None)
                print("JSON Parsing error.")
        else:
            callback(None)
            print(f"REST API Error: {reply.errorString()}")

        reply.deleteLater()

    @staticmethod
    def _on_sensor_data_fetched(reply: QNetworkReply, callback):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            raw_data = reply.readAll().data().decode('utf-8')
            try:
                payload = json.loads(raw_data)
                if isinstance(payload, list):
                    callback(payload) #return raw json data as is 
                else:
                    callback(None)
            except json.JSONDecodeError:
                callback(None)
                print("JSON Parsing error.")
        else:
            callback(None)
            print(f"REST API Error: {reply.errorString()}")
            
        reply.deleteLater()

    @staticmethod
    def _on_status_fetched(reply: QNetworkReply, callback) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            raw_data = reply.readAll().data().decode('utf-8')
            try:
                callback(json.loads(raw_data))
            except json.JSONDecodeError:
                callback(None)
        else:
            callback(None)
        reply.deleteLater()

    @staticmethod
    def _on_health_fetched(reply: QNetworkReply, callback) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            raw_data = reply.readAll().data().decode('utf-8')
            try:
                payload = json.loads(raw_data)
                callback(payload.get("status", "unknown"))
            except json.JSONDecodeError:
                callback(None)
        else:
            callback(None)
        reply.deleteLater()


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
