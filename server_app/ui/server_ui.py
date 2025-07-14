from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel
from PyQt6.QtCore import Qt

class ServerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Messenger Server")
        self.setGeometry(100, 100, 500, 400)
        self.server_running = False  # Track server state
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        self.status_label = QLabel("Server Status: Not Running")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

        self.start_button = QPushButton("Start Server")
        self.start_button.clicked.connect(self.toggle_server)  # Toggle function
        layout.addWidget(self.start_button)

        self.setLayout(layout)

    def append_log(self, message):
        self.log_area.append(message)

    def update_status(self, status):
        self.status_label.setText(f"Server Status: {status}")

    def toggle_server(self):
        if self.server_running:
            self.stop_server()
        else:
            self.start_server()

    def start_server(self):
        self.server_running = True
        self.update_status("Running")
        self.start_button.setText("Stop Server")

    def stop_server(self):
        self.server_running = False
        self.update_status("Stopped")
        self.start_button.setText("Start Server")
