import sys
import socket
import threading
import json
import uuid
import sqlite3
import errno
from PyQt6.QtWidgets import QApplication
from .ui.server_ui import ServerUI
from shared.config import HOST, PORT, BUFFER_SIZE, ENCODING, DB_NAME
from .python_db import (
    init_db, add_user, get_user, create_chat, get_user_chats,
    add_message, get_chat_messages, get_chat_members,
    add_users_to_chat, remove_user_from_chat, delete_chat
)

sessions = {}  # socket -> keyword


class ServerApp:
    def __init__(self):
        self.running = False
        self.accept_thread = None
        self.clients = []
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ui = ServerUI()
        self.ui.start_button.clicked.connect(self.toggle_server)

    def toggle_server(self):
        if self.running:
            self.stop_server()
        else:
            self.start_server()

    def start_server(self):
        if self.running:
            self.ui.append_log("Server is already running.")
            return

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen()
            self.running = True

            self.ui.update_status("Running")
            self.ui.append_log(f"✅ Server started on {HOST}:{PORT}")
            self.ui.start_button.setText("Stop Server")

            self.accept_thread = threading.Thread(target=self.accept_clients, daemon=True)
            self.accept_thread.start()
        except Exception as e:
            self.ui.append_log(f"❌ Failed to start server: {e}")

    def stop_server(self):
        self.running = False
        self.ui.update_status("Stopped")
        self.ui.append_log("🛑 Server stopping...")

        # Close all client sockets
        for client in self.clients:
            try:
                client.shutdown(socket.SHUT_RDWR)
                client.close()
            except Exception:
                pass
        self.clients.clear()

        # Close the server socket
        try:
            self.server_socket.close()
        except Exception:
            pass

        self.ui.start_button.setText("Start Server")
        self.ui.append_log("✅ Server stopped.")

    def accept_clients(self):
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
            except OSError:
                break  # Server was stopped, socket closed

            if not self.running:
                client_socket.close()
                break

            self.clients.append(client_socket)
            self.ui.append_log(f"Client connected from {addr}")
            threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()

    def handle_client(self, client_socket):
        try:
            while True:
                try:
                    data = client_socket.recv(BUFFER_SIZE).decode(ENCODING)
                except OSError as e:
                    if e.errno == errno.WSAENOTSOCK:
                        break  # Client socket already closed
                    raise  # Reraise others
                if not data:
                    break
                
                request = json.loads(data)
                action = request.get("action")
                username = sessions.get(client_socket)

                match action:
                    case "register":
                        self.handle_register(client_socket, request)
                    case "login":
                        self.handle_login(client_socket, request)
                    case "send_message":
                        self.handle_send_message(client_socket, request)
                    case "get_chats":
                        self.handle_get_chats(client_socket, request)
                    case "create_chat":
                        self.handle_create_chat(client_socket, request)
                    case "add_users_to_chat":
                        self.handle_add_users_to_chat(client_socket, request, username)
                    case "leave_chat":
                        self.handle_leave_chat(client_socket, request, username)
                    case "delete_chat":
                        self.handle_delete_chat(client_socket, request, username)
                    case "get_chat_messages":
                        self.handle_get_chat_messages(client_socket, request, username)
                    case _:
                        self.send_response(client_socket, {"status": "error", "message": "Unknown action"})

        except Exception as e:
            if isinstance(e, ConnectionResetError) or (hasattr(e, 'errno') and e.errno == errno.WSAECONNRESET):
                self.ui.append_log("Client closed the connection unexpectedly.")
            elif isinstance(e, OSError) and e.errno == errno.WSAENOTSOCK:
                self.ui.append_log("Client socket was already closed.")
            else:
                self.ui.append_log(f"Client error: {e}")
        finally:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            if client_socket in sessions:
                self.ui.append_log(f"User disconnected: @{sessions[client_socket]}")
                del sessions[client_socket]
            try:
                client_socket.close()
            except Exception:
                pass

    # ========================
    #        HANDLERS
    # ========================

    def handle_register(self, client_socket, data):
        keyword = data.get("keyword")
        nickname = data.get("nickname")
        password = data.get("password")

        if not keyword or not nickname or not password:
            self.send_response(client_socket, {"status": "error", "message": "Missing fields"})
            return

        success = add_user(keyword, nickname, password)
        if success:
            group_chat_id = self.get_or_create_default_chat("Group Chat")
            add_users_to_chat(group_chat_id, [keyword])
            self.ui.append_log(f"New user registered: @{keyword} ({nickname})")
            self.send_response(client_socket, {"status": "ok"})
        else:
            self.send_response(client_socket, {"status": "error", "message": "Keyword already taken"})

    def handle_login(self, client_socket, data):
        keyword = data.get("keyword")
        password = data.get("password")

        user = get_user(keyword)
        if user and user[2] == password:
            sessions[client_socket] = keyword
            self.ui.append_log(f"User logged in: @{keyword}")
            self.send_response(client_socket, {"status": "ok", "nickname": user[1]})
        else:
            self.send_response(client_socket, {"status": "error", "message": "Invalid credentials"})

    def handle_send_message(self, client_socket, data):
        keyword = sessions.get(client_socket)
        chat_id = data.get("chat_id")
        message = data.get("message")

        if not keyword or not chat_id or not message:
            self.send_response(client_socket, {"status": "error", "message": "Missing fields"})
            return

        members = get_chat_members(chat_id)
        if keyword not in members:
            self.send_response(client_socket, {"status": "error", "message": "Not a member of this chat"})
            return

        add_message(chat_id, keyword, message)
        response = {
            "action": "new_message",
            "chat_id": chat_id,
            "from": keyword,
            "message": message
        }
        self.broadcast_to_chat(chat_id, response)

    def handle_get_chats(self, client_socket, _):
        keyword = sessions.get(client_socket)
        if not keyword:
            self.send_response(client_socket, {"status": "error", "message": "Not logged in"})
            return

        chats = get_user_chats(keyword)
        chat_list = [{"id": cid, "name": name} for cid, name in chats]
        self.send_response(client_socket, {"status": "ok", "chats": chat_list})

    def handle_create_chat(self, client_socket, data):
        keyword = sessions.get(client_socket)
        if not keyword:
            self.send_response(client_socket, {"status": "error", "message": "Not logged in"})
            return

        chat_name = data.get("name")
        members = data.get("members", [])

        if not chat_name:
            self.send_response(client_socket, {"status": "error", "message": "Missing chat name"})
            return

        if keyword not in members:
            members.append(keyword)

        invalid_members = [m for m in members if get_user(m) is None]
        if invalid_members:
            self.send_response(client_socket, {"status": "error", "message": f"Invalid members: {invalid_members}"})
            return

        chat_id = create_chat(chat_name, members)
        self.ui.append_log(f"Chat created: {chat_name} by @{keyword}")
        self.send_response(client_socket, {"status": "ok", "chat_id": chat_id})

        for member in members:
            self.notify_user_chat_list_update(member)

    def handle_add_users_to_chat(self, client_socket, data, username):
        chat_id = data.get("chat_id")
        new_members = data.get("users", [])

        if not username or not chat_id:
            self.send_response(client_socket, {"status": "error", "message": "Missing fields"})
            return

        current_members = get_chat_members(chat_id)
        if username not in current_members:
            self.send_response(client_socket, {"status": "error", "message": "You are not in this chat"})
            return

        invalid = [u for u in new_members if get_user(u) is None]
        if invalid:
            self.send_response(client_socket, {"status": "error", "message": f"Invalid users: {invalid}"})
            return

        for member in new_members:
            if member not in current_members:
                add_users_to_chat(chat_id, [member])
                self.notify_user_chat_list_update(member)

        self.send_response(client_socket, {"status": "ok"})

    def handle_leave_chat(self, client_socket, data, username):
        chat_id = data.get("chat_id")
        if not username or not chat_id:
            self.send_response(client_socket, {"status": "error", "message": "Missing fields"})
            return

        members = get_chat_members(chat_id)
        if username not in members:
            self.send_response(client_socket, {"status": "error", "message": "You are not in this chat"})
            return

        remove_user_from_chat(chat_id, username)
        self.send_response(client_socket, {"status": "ok"})
        self.notify_user_chat_list_update(username)

    def handle_delete_chat(self, client_socket, data, username):
        chat_id = data.get("chat_id")
        if not username or not chat_id:
            self.send_response(client_socket, {"status": "error", "message": "Missing fields"})
            return

        members = get_chat_members(chat_id)
        if username not in members:
            self.send_response(client_socket, {"status": "error", "message": "You are not in this chat"})
            return

        delete_chat(chat_id)
        self.send_response(client_socket, {"status": "ok"})

        for member in members:
            self.notify_user_chat_list_update(member)

    def handle_get_chat_messages(self, client_socket, data, username):
        chat_id = data.get("chat_id")
        if not username or not chat_id:
            self.send_response(client_socket, {"status": "error", "message": "Missing fields"})
            return

        members = get_chat_members(chat_id)
        if username not in members:
            self.send_response(client_socket, {"status": "error", "message": "You are not in this chat"})
            return

        messages = get_chat_messages(chat_id)
        formatted = [{"from": sender, "message": msg} for sender, msg in messages]
        self.send_response(client_socket, {"action": "chat_messages", "messages": formatted})

    # ========================
    #    SUPPORT FUNCTIONS
    # ========================

    def send_response(self, client_socket, response_dict):
        try:
            client_socket.send(json.dumps(response_dict).encode(ENCODING))
        except:
            pass

    def broadcast_to_chat(self, chat_id, response_dict):
        data = json.dumps(response_dict).encode(ENCODING)
        members = get_chat_members(chat_id)
        for sock, keyword in sessions.items():
            if keyword in members:
                try:
                    sock.send(data)
                except:
                    pass

    def notify_user_chat_list_update(self, keyword):
        for sock, kw in sessions.items():
            if kw == keyword:
                try:
                    sock.send(json.dumps({"action": "chat_list_updated"}).encode(ENCODING))
                except:
                    pass

    def get_or_create_default_chat(self, name):
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.execute("SELECT id FROM chats WHERE name = ?", (name,))
            row = cur.fetchone()
            if row:
                return row[0]
        return create_chat(name, [])


def main():
    init_db()
    app = QApplication(sys.argv)
    server = ServerApp()
    server.ui.show()
    server.ui.append_log("Server initialized and ready.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
