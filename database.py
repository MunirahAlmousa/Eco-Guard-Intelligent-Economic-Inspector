import sqlite3
import hashlib
import hmac
import os
import secrets

DB_PATH = "/tmp/eco_guard.db"

SECRET_KEY = os.environ.get("SECRET_KEY", "default-change-this-in-production")

def hash_password(password: str) -> str:
    salt = secrets.token_hex(32)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=260000
    )
    return f"{salt}${key.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, key_hex = stored_hash.split('$')
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations=260000
        )
        return hmac.compare_digest(key.hex(), key_hex)
    except Exception:
        return False

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("PRAGMA journal_mode=WAL")

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            login_attempts INTEGER DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success INTEGER
        )
    ''')

    admin_password = os.environ.get("ADMIN_PASSWORD", "1234")
    admin_hash = hash_password(admin_password)
    c.execute('''
        INSERT OR IGNORE INTO users (username, password_hash, role)
        VALUES (?, ?, ?)
    ''', ("eco", admin_hash, "admin"))

    conn.commit()
    conn.close()

def register_user(username: str, password: str) -> dict:
    if len(username.strip()) < 3:
        return {"success": False, "message": "اسم المستخدم يجب أن يكون 3 أحرف على الأقل"}
    if len(password) < 6:
        return {"success": False, "message": "كلمة المرور يجب أن تكون 6 أحرف على الأقل"}

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username.strip(), hash_password(password), "user")
        )
        c.execute(
            "INSERT INTO audit_log (username, action, success) VALUES (?, ?, ?)",
            (username.strip(), "register", 1)
        )
        conn.commit()
        conn.close()
        return {"success": True, "message": "تم إنشاء الحساب بنجاح"}
    except sqlite3.IntegrityError:
        return {"success": False, "message": "اسم المستخدم موجود مسبقاً"}

def login_user(username: str, password: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        "SELECT id, username, role, password_hash, login_attempts FROM users WHERE username=?",
        (username.strip(),)
    )
    user = c.fetchone()

    if not user:
        c.execute(
            "INSERT INTO audit_log (username, action, success) VALUES (?, ?, ?)",
            (username.strip(), "login_failed", 0)
        )
        conn.commit()
        conn.close()
        return {"success": False, "message": "اسم المستخدم أو كلمة المرور غير صحيحة"}

    user_id, user_name, role, stored_hash, attempts = user

    if attempts >= 10:
        conn.close()
        return {"success": False, "message": "الحساب مقفل بسبب كثرة المحاولات — تواصل مع المدير"}

    if verify_password(password, stored_hash):
        c.execute(
            "UPDATE users SET login_attempts=0, last_login=CURRENT_TIMESTAMP WHERE id=?",
            (user_id,)
        )
        c.execute(
            "INSERT INTO audit_log (username, action, success) VALUES (?, ?, ?)",
            (user_name, "login_success", 1)
        )
        conn.commit()
        conn.close()
        return {"success": True, "id": user_id, "username": user_name, "role": role}
    else:
        c.execute(
            "UPDATE users SET login_attempts=login_attempts+1 WHERE id=?",
            (user_id,)
        )
        c.execute(
            "INSERT INTO audit_log (username, action, success) VALUES (?, ?, ?)",
            (user_name, "login_failed", 0)
        )
        conn.commit()
        conn.close()
        return {"success": False, "message": "اسم المستخدم أو كلمة المرور غير صحيحة"}

def get_all_users() -> list:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username, role, created_at FROM users ORDER BY created_at DESC")
    users = c.fetchall()
    conn.close()
    return users

def delete_user(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=? AND role != 'admin'", (user_id,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def log_analysis(username: str, analysis_type: str, records_count: int = 1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO audit_log (username, action, success) VALUES (?, ?, ?)",
        (username, f"analysis_{analysis_type}_{records_count}_records", 1)
    )
    conn.commit()
    conn.close()

def get_audit_log(limit: int = 100) -> list:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT username, action, timestamp, success
        FROM audit_log
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    logs = c.fetchall()
    conn.close()
    return logs