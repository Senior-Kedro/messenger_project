from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QTextEdit, QVBoxLayout, QHBoxLayout, QSplitter
)
from PyQt6.QtCore import Qt


class ClientUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 Messenger Client")
        self.resize(900, 600)

        # Left pane: Chats list + chat creation
        self.chat_list_widget = QListWidget()

        # Chat creation controls
        self.chat_name_input = QLineEdit()
        self.chat_name_input.setPlaceholderText("Chat Name")

        self.chat_members_input = QLineEdit()
        self.chat_members_input.setPlaceholderText("Members (comma-separated keywords)")

        self.create_chat_button = QPushButton("Create Chat")

        chat_creation_layout = QVBoxLayout()
        chat_creation_layout.addWidget(QLabel("Create New Chat"))
        chat_creation_layout.addWidget(self.chat_name_input)
        chat_creation_layout.addWidget(self.chat_members_input)
        chat_creation_layout.addWidget(self.create_chat_button)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Chats"))
        left_layout.addWidget(self.chat_list_widget)
        left_layout.addLayout(chat_creation_layout)

        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        # Right pane: Messages + message input + login/register + logs

        # Login/Register area
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("Keyword (@username)")

        self.nickname_input = QLineEdit()
        self.nickname_input.setPlaceholderText("Nickname")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.login_button = QPushButton("Login")
        self.register_button = QPushButton("Register")

        login_layout = QHBoxLayout()
        login_layout.addWidget(self.keyword_input)
        login_layout.addWidget(self.nickname_input)
        login_layout.addWidget(self.password_input)
        login_layout.addWidget(self.login_button)
        login_layout.addWidget(self.register_button)

        # Messages display
        self.chat_messages = QTextEdit()
        self.chat_messages.setReadOnly(True)

        # Message input area
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your message here...")
        self.send_button = QPushButton("Send")

        message_layout = QHBoxLayout()
        message_layout.addWidget(self.message_input)
        message_layout.addWidget(self.send_button)

        # Chat management area (add users, leave, delete)
        self.add_users_input = QLineEdit()
        self.add_users_input.setPlaceholderText("Add users (comma-separated keywords)")
        self.add_users_button = QPushButton("Add Users")
        self.leave_chat_button = QPushButton("Leave Chat")
        self.delete_chat_button = QPushButton("Delete Chat")

        chat_manage_layout = QHBoxLayout()
        chat_manage_layout.addWidget(self.add_users_input)
        chat_manage_layout.addWidget(self.add_users_button)
        chat_manage_layout.addWidget(self.leave_chat_button)
        chat_manage_layout.addWidget(self.delete_chat_button)

        # Logs area
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFixedHeight(120)

        # Reconnect button (initially hidden/disabled)
        self.reconnect_button = QPushButton("Reconnect")
        self.reconnect_button.setEnabled(False)

        right_layout = QVBoxLayout()
        right_layout.addLayout(login_layout)
        right_layout.addWidget(QLabel("Chat Messages"))
        right_layout.addWidget(self.chat_messages)
        right_layout.addLayout(message_layout)
        right_layout.addLayout(chat_manage_layout)
        right_layout.addWidget(QLabel("Logs"))
        right_layout.addWidget(self.log_console)
        right_layout.addWidget(self.reconnect_button)

        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        # Main splitter (left + right)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setStretchFactor(1, 3)

        main_layout = QHBoxLayout()
        main_layout.addWidget(main_splitter)

        self.setLayout(main_layout)

    def append_log(self, text: str):
        self.log_console.append(text)

    def append_chat_message(self, text: str):
        self.chat_messages.append(text)

    def create_chat_list_item(self, name: str, chat_id: str) -> QListWidgetItem:
        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, chat_id)
        return item
