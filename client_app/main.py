import sys
import socket
import threading
import json
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from .ui.client_ui import ClientUI
from shared.config import HOST, PORT, BUFFER_SIZE, ENCODING


class ResponseHandler(QObject):
    response_received = pyqtSignal(dict)


class ClientApp:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ui = ClientUI()

        self.ui.login_button.clicked.connect(self.login)
        self.ui.register_button.clicked.connect(self.register)
        self.ui.send_button.clicked.connect(self.send_message)
        self.ui.create_chat_button.clicked.connect(self.create_chat)

        self.ui.chat_list_widget.currentItemChanged.connect(self.change_chat)
        self.ui.add_users_button.clicked.connect(self.add_users_to_chat)
        self.ui.leave_chat_button.clicked.connect(self.leave_chat)
        self.ui.delete_chat_button.clicked.connect(self.delete_chat)

        self.current_chat_id = None
        self.keyword = None
        self.nickname = None

        self.response_handler = ResponseHandler()
        self.response_handler.response_received.connect(self.handle_response)

        self.connection_lost_shown = False

        try:
            self.socket.connect((HOST, PORT))
            threading.Thread(target=self.receive_messages, daemon=True).start()
            self.ui.append_log(f"Connected to server {HOST}:{PORT}")
        except Exception as e:
            if hasattr(e, 'winerror') and e.winerror == 10061:
                msg = "Couldn't connect to the server, most likely it is down. Please wait and try again later."
            else:
                msg = f"Could not connect to server: {e}"
            self.ui.append_log(f"Connection failed: {msg}")
            QMessageBox.critical(self.ui, "Connection Error", msg)
            self.disable_ui_on_disconnect()
            self.ui.reconnect_button.clicked.connect(self.try_reconnect)
            self.ui.reconnect_button.setEnabled(True)

    def login(self):
        keyword = self.ui.keyword_input.text().strip()
        password = self.ui.password_input.text().strip()
        if not keyword or not password:
            QMessageBox.warning(self.ui, "Input Error", "Keyword and password required")
            return

        self.send({
            "action": "login",
            "keyword": keyword,
            "password": password
        })

    def register(self):
        keyword = self.ui.keyword_input.text().strip()
        nickname = self.ui.nickname_input.text().strip()
        password = self.ui.password_input.text().strip()

        if not keyword or not nickname or not password:
            QMessageBox.warning(self.ui, "Input Error", "Keyword, nickname, and password required")
            return

        self.send({
            "action": "register",
            "keyword": keyword,
            "nickname": nickname,
            "password": password
        })

    def send_message(self):
        message = self.ui.message_input.text().strip()
        if not message:
            return
        if not self.current_chat_id:
            QMessageBox.warning(self.ui, "No Chat Selected", "Select a chat first")
            return

        self.send({
            "action": "send_message",
            "chat_id": self.current_chat_id,
            "message": message
        })
        self.ui.message_input.clear()

    def create_chat(self):
        name = self.ui.chat_name_input.text().strip()
        members_text = self.ui.chat_members_input.text().strip()
        members = [m.strip() for m in members_text.split(",") if m.strip()]

        if not name:
            QMessageBox.warning(self.ui, "Input Error", "Chat name required")
            return

        self.send({
            "action": "create_chat",
            "name": name,
            "members": members
        })


    def change_chat(self, current, previous=None):
        if current:
            self.current_chat_id = current.data(Qt.ItemDataRole.UserRole)
            self.ui.chat_messages.clear()
            self.request_chat_messages(self.current_chat_id)
        else:
            self.current_chat_id = None
            self.ui.chat_messages.clear()

    def add_users_to_chat(self):
        if not self.current_chat_id:
            QMessageBox.warning(self.ui, "No Chat Selected", "Select a chat first")
            return

        users_text = self.ui.add_users_input.text().strip()
        if not users_text:
            QMessageBox.warning(self.ui, "Input Error", "Enter user keywords to add")
            return

        users = [u.strip() for u in users_text.split(",") if u.strip()]
        self.send({
            "action": "add_users_to_chat",
            "chat_id": self.current_chat_id,
            "users": users
        })
        self.ui.add_users_input.clear()

    def leave_chat(self):
        if not self.current_chat_id:
            QMessageBox.warning(self.ui, "No Chat Selected", "Select a chat first")
            return
        self.send({
            "action": "leave_chat",
            "chat_id": self.current_chat_id
        })

    def delete_chat(self):
        if not self.current_chat_id:
            QMessageBox.warning(self.ui, "No Chat Selected", "Select a chat first")
            return
        self.send({
            "action": "delete_chat",
            "chat_id": self.current_chat_id
        })

    def request_chat_messages(self, chat_id):
        self.send({
            "action": "get_chat_messages",
            "chat_id": chat_id
        })

    def send(self, data_dict):
        try:
            data = json.dumps(data_dict)
            self.socket.sendall(data.encode(ENCODING))
        except Exception as e:
            self.ui.append_log(f"Send Error: {e}")
            QMessageBox.critical(self.ui, "Send Error", f"Failed to send data: {e}")

    def receive_messages(self):
        try:
            while True:
                try:
                    data = self.socket.recv(BUFFER_SIZE).decode(ENCODING)
                    if not data:
                        raise ConnectionResetError("Server closed the connection.")
                    response = json.loads(data)
                    self.response_handler.response_received.emit(response)
                except json.JSONDecodeError:
                    self.ui.append_log("Received invalid data from server.")
                except (ConnectionResetError, ConnectionAbortedError):
                    raise  # Let outer loop handle it
        except (OSError, ConnectionResetError, ConnectionAbortedError) as e:
            self.response_handler.response_received.emit({
                "status": "error",
                "message": "Connection to server lost. Please try restarting the client."
            })
        except Exception as e:
            self.response_handler.response_received.emit({
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            })


    def handle_response(self, response):
        status = response.get("status")
        if status == "error":
            error_msg = response.get("message", "Unknown error")
            
            if "connection" in error_msg.lower() and not self.connection_lost_shown:
                self.ui.append_log("⚠️ Server connection lost.")
                QMessageBox.warning(self.ui, "Disconnected", error_msg)
                self.disable_ui_on_disconnect()

                self.ui.reconnect_button.setEnabled(True)
                self.connection_lost_shown = True
            else:
                self.ui.append_log(f"Error: {error_msg}")
                QMessageBox.warning(self.ui, "Operation Failed", error_msg)
            return

        action = response.get("action", "")

        if action == "new_message":
            chat_id = response.get("chat_id")
            sender = response.get("from")
            message = response.get("message")
            if chat_id == self.current_chat_id:
                self.ui.append_chat_message(f"@{sender}: {message}")

        elif action == "chat_messages":
            messages = response.get("messages", [])
            self.ui.chat_messages.clear()
            for msg in messages:
                self.ui.append_chat_message(f"@{msg['from']}: {msg['message']}")

        elif action == "chat_list_updated":
            self.ui.append_log("Chat list updated")
            self.request_chats()

        elif "nickname" in response:
            self.nickname = response["nickname"]
            self.ui.append_log(f"Logged in as {self.nickname}")
            self.keyword = self.ui.keyword_input.text().strip()
            self.request_chats()

        elif "chats" in response:
            self.ui.chat_list_widget.clear()
            for chat in response["chats"]:
                item = self.ui.create_chat_list_item(chat["name"], chat["id"])
                self.ui.chat_list_widget.addItem(item)
            self.ui.append_log("Chats updated")

        elif "chat_id" in response:
            self.ui.append_log(f"Chat created with id {response['chat_id']}")
            self.request_chats()

        elif status == "ok":
            self.ui.append_log("Operation succeeded")

        if action in ("delete_chat", "leave_chat"):
            self.current_chat_id = None
            self.request_chats()
            self.ui.chat_messages.clear()

    def disable_ui_on_disconnect(self):
        self.ui.login_button.setEnabled(False)
        self.ui.register_button.setEnabled(False)
        self.ui.send_button.setEnabled(False)
        self.ui.create_chat_button.setEnabled(False)
        self.ui.add_users_button.setEnabled(False)
        self.ui.leave_chat_button.setEnabled(False)
        self.ui.delete_chat_button.setEnabled(False)
        self.ui.append_log("All actions disabled due to disconnection.")

    def enable_ui_after_reconnect(self):
        self.ui.login_button.setEnabled(True)
        self.ui.register_button.setEnabled(True)
        self.ui.send_button.setEnabled(True)
        self.ui.create_chat_button.setEnabled(True)
        self.ui.add_users_button.setEnabled(True)
        self.ui.leave_chat_button.setEnabled(True)
        self.ui.delete_chat_button.setEnabled(True)

    def try_reconnect(self):
        try:
            # Replace old socket safely
            try:
                old_socket = self.socket
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                old_socket.close()
            except Exception:
                pass

            # Try to connect
            self.socket.connect((HOST, PORT))
            threading.Thread(target=self.receive_messages, daemon=True).start()

            self.ui.append_log(f"Reconnected to server {HOST}:{PORT}")
            QMessageBox.information(self.ui, "Reconnected", "Successfully reconnected to the server.")

            self.enable_ui_after_reconnect()
            self.ui.reconnect_button.setEnabled(False)
            self.connection_lost_shown = False

        except Exception as e:
            if hasattr(e, 'winerror') and e.winerror == 10061:
                msg = "Couldn't connect to the server, most likely it is down. Please wait and try again later."
            else:
                msg = f"Could not connect to server: {e}"
            self.ui.append_log(f"Reconnect failed: {msg}")
            QMessageBox.critical(self.ui, "Reconnect Failed", f"Could not reconnect: {msg}")

    def request_chats(self):
        self.send({"action": "get_chats"})

    def close_connection(self):
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except Exception:
            pass


def main():
    app = QApplication(sys.argv)
    client = ClientApp()
    client.ui.show()
    exit_code = app.exec()
    client.close_connection()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
