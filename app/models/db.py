# 数据库链接与建表
import os
import sqlite3


# 获得项目根路径的方法
def _project_root():
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )

# 获得数据库文件路径
DB_PATH = os.path.join(_project_root(), "database", "app.db")

# 获得数据库连接
def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 
def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users(
                id integer PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                status INTEGER NOT NULL DEFAULT 1,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )

        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'role' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")

        if 'status' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN status INTEGER NOT NULL DEFAULT 1")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS roles(
                id integer PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                description TEXT,
                permissions TEXT,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_roles(
                id integer PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                create_at TEXT NOT NULL DEFAULT(datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(role_id) REFERENCES roles(id)
            )
            """
        )

        cursor = conn.execute("SELECT COUNT(*) FROM roles")
        if cursor.fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO roles(name, display_name, description, permissions) VALUES(?, ?, ?, ?)",
                ("admin", "系统管理员", "拥有系统所有权限", "*")
            )
            conn.execute(
                "INSERT INTO roles(name, display_name, description, permissions) VALUES(?, ?, ?, ?)",
                ("user", "普通用户", "普通用户权限", "user:view")
            )