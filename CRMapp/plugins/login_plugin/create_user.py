import sqlite3, os
from werkzeug.security import generate_password_hash

DB_FILE = os.path.join(os.path.dirname(__file__), "login_plugin.db")

username = input("Username: ")
password = input("Password: ")

with sqlite3.connect(DB_FILE) as conn:
    conn.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        (username, generate_password_hash(password))
    )
print("✅ User created.")
