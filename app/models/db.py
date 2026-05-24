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
    conn.execute("PRAGMA foreign_keys = ON")
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
            CREATE TABLE IF NOT EXISTS permissions(
                id integer PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                code TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL DEFAULT 'menu',
                parent_id INTEGER DEFAULT 0,
                icon TEXT,
                url TEXT,
                sort_order INTEGER DEFAULT 0,
                status INTEGER DEFAULT 1,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS roles(
                id integer PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                description TEXT,
                is_system INTEGER DEFAULT 0,
                status INTEGER DEFAULT 1,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )

        cursor = conn.execute("PRAGMA table_info(roles)")
        role_columns = [row[1] for row in cursor.fetchall()]
        
        if 'is_system' not in role_columns:
            conn.execute("ALTER TABLE roles ADD COLUMN is_system INTEGER DEFAULT 0")
        
        if 'status' not in role_columns:
            conn.execute("ALTER TABLE roles ADD COLUMN status INTEGER DEFAULT 1")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS role_permissions(
                id integer PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                permission_id INTEGER NOT NULL,
                create_at TEXT NOT NULL DEFAULT(datetime('now')),
                FOREIGN KEY(role_id) REFERENCES roles(id) ON DELETE CASCADE,
                FOREIGN KEY(permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
                UNIQUE(role_id, permission_id)
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
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(role_id) REFERENCES roles(id) ON DELETE CASCADE
            )
            """
        )

        cursor = conn.execute("SELECT COUNT(*) FROM roles")
        if cursor.fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO roles(name, display_name, description, is_system, status) VALUES(?, ?, ?, ?, ?)",
                ("admin", "超级管理员", "系统超级管理员，拥有所有权限", 1, 1)
            )
            conn.execute(
                "INSERT INTO roles(name, display_name, description, is_system, status) VALUES(?, ?, ?, ?, ?)",
                ("user", "普通用户", "普通用户角色，默认权限", 0, 1)
            )

        cursor = conn.execute("SELECT COUNT(*) FROM permissions")
        if cursor.fetchone()[0] == 0:
            conn.execute("INSERT INTO permissions(name, display_name, code, category, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?)",
                ("系统管理", "系统管理", "system", "group", "fas fa-cog", "", 100))
            conn.execute("INSERT INTO permissions(name, display_name, code, category, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?)",
                ("用户管理", "用户管理", "user", "menu", "fas fa-users", "/admin/user", 101))
            conn.execute("INSERT INTO permissions(name, display_name, code, category, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?)",
                ("角色管理", "角色管理", "role", "menu", "fas fa-user-shield", "/admin/role", 102))
            conn.execute("INSERT INTO permissions(name, display_name, code, category, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?)",
                ("权限管理", "权限管理", "permission", "menu", "fas fa-key", "/admin/permission", 103))
            conn.execute("INSERT INTO permissions(name, display_name, code, category, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?)",
                ("数字员工", "数字员工", "robot", "group", "fas fa-robot", "", 200))
            conn.execute("INSERT INTO permissions(name, display_name, code, category, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?)",
                ("数据员工", "数据员工", "data_robot", "menu", "fas fa-database", "/admin/robot/data", 201))
            conn.execute("INSERT INTO permissions(name, display_name, code, category, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?)",
                ("瞭望管理", "瞭望管理", "lookout", "group", "fas fa-binoculars", "", 300))
            conn.execute("INSERT INTO permissions(name, display_name, code, category, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?)",
                ("瞭望源管理", "瞭望源管理", "lookout_source", "menu", "fas fa-globe", "/admin/lookout/source", 301))

            conn.execute("INSERT INTO role_permissions(role_id, permission_id) SELECT 1, id FROM permissions")
