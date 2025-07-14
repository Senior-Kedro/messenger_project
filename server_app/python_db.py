from shared.config import DB_NAME
import sqlite3
import uuid

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            keyword TEXT PRIMARY KEY,
            nickname TEXT NOT NULL,
            password TEXT NOT NULL
        );
    """)

    # Chats table (no type)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );
    """)

    # Chat members table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_members (
            chat_id TEXT,
            keyword TEXT,
            PRIMARY KEY (chat_id, keyword),
            FOREIGN KEY (chat_id) REFERENCES chats(id),
            FOREIGN KEY (keyword) REFERENCES users(keyword)
        );
    """)

    # Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            sender TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats(id)
        );
    """)

    conn.commit()
    conn.close()

def add_user(keyword, nickname, password):
    with sqlite3.connect(DB_NAME) as conn:
        try:
            conn.execute(
                "INSERT INTO users (keyword, nickname, password) VALUES (?, ?, ?)",
                (keyword, nickname, password)
            )
            return True
        except sqlite3.IntegrityError:
            return False

def get_user(keyword):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.execute(
            "SELECT keyword, nickname, password FROM users WHERE keyword = ?",
            (keyword,)
        )
        return cur.fetchone()

def create_chat(name, members):
    chat_id = str(uuid.uuid4())
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT INTO chats (id, name) VALUES (?, ?)", (chat_id, name))
        for member in members:
            conn.execute(
                "INSERT INTO chat_members (chat_id, keyword) VALUES (?, ?)",
                (chat_id, member)
            )
    return chat_id

def get_user_chats(keyword):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.execute("""
            SELECT c.id, c.name
            FROM chats c
            JOIN chat_members cm ON c.id = cm.chat_id
            WHERE cm.keyword = ?
        """, (keyword,))
        return cur.fetchall()

def add_message(chat_id, sender, content):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "INSERT INTO messages (chat_id, sender, content) VALUES (?, ?, ?)",
            (chat_id, sender, content)
        )

def get_chat_messages(chat_id):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.execute(
            "SELECT sender, content FROM messages WHERE chat_id = ? ORDER BY id",
            (chat_id,)
        )
        return cur.fetchall()

def get_chat_members(chat_id):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.execute(
            "SELECT keyword FROM chat_members WHERE chat_id = ?",
            (chat_id,)
        )
        return set(row[0] for row in cur.fetchall())

def add_users_to_chat(chat_id, users):
    with sqlite3.connect(DB_NAME) as conn:
        for user in users:
            conn.execute(
                "INSERT OR IGNORE INTO chat_members (chat_id, keyword) VALUES (?, ?)",
                (chat_id, user)
            )

def remove_user_from_chat(chat_id, keyword):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "DELETE FROM chat_members WHERE chat_id = ? AND keyword = ?",
            (chat_id, keyword)
        )

def delete_chat(chat_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        conn.execute("DELETE FROM chat_members WHERE chat_id = ?", (chat_id,))
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
