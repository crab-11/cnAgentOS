import hashlib
import secrets
import sqlite3

from app.models.db import get_connection

# 密码加密方法
def _hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100_000
    )
    return dk.hex()

# 用户对象类
class UserRepository:
    @staticmethod
    def _get_role_by_id(conn, role_id):
        if not role_id:
            return None
        return conn.execute(
            "SELECT id, name, display_name FROM roles WHERE id = ? AND status = 1",
            (role_id,)
        ).fetchone()

    @staticmethod
    def _get_role_by_name(conn, name):
        return conn.execute(
            "SELECT id, name, display_name FROM roles WHERE name = ? AND status = 1",
            (name,)
        ).fetchone()

    @staticmethod
    def _set_user_role(conn, user_id, role_id):
        role = UserRepository._get_role_by_id(conn, role_id)
        if not role:
            return False

        conn.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
        conn.execute(
            "INSERT INTO user_roles(user_id, role_id) VALUES(?, ?)",
            (user_id, role["id"])
        )
        conn.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (role["name"], user_id)
        )
        return True

    # 创建用户方法
    @staticmethod
    def create_user(username: str, password: str, role: str = "user", status: int = 1, role_id: int = None, nickname: str = None, email: str = None) -> bool:
        salt = secrets.token_bytes(16)
        password_hash = _hash_password(password, salt)

        try:
            with get_connection() as conn:
                role_row = (
                    UserRepository._get_role_by_id(conn, role_id)
                    if role_id else
                    UserRepository._get_role_by_name(conn, role)
                )
                role_code = role_row["name"] if role_row else role

                cursor = conn.execute(
                    "insert into users(username, nickname, email, password_hash, salt, role, status) values(?, ?, ?, ?, ?, ?, ?)",
                    (username, nickname, email, password_hash, salt.hex(), role_code, status)
                )
                if role_row:
                    UserRepository._set_user_role(conn, cursor.lastrowid, role_row["id"])
            return True
        except sqlite3.IntegrityError:
            return False

    # 通过用户名检索用户信息
    @staticmethod
    def get_user_by_username(username: str):
        with get_connection() as conn:
            row = conn.execute(
                "select id, username, nickname, email, password_hash, salt, role, status, last_login_at from users where username = ?",
                (username,)
            ).fetchone()
        return row

    # 通过ID获取用户
    @staticmethod
    def get_user_by_id(user_id: int):
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT u.id, u.username, u.nickname, u.email, u.role, u.status, u.last_login_at, u.create_at,
                       r.id AS role_id, r.name AS role_code, r.display_name AS role_name
                FROM users u
                LEFT JOIN (
                    SELECT user_id, MIN(role_id) AS role_id
                    FROM user_roles
                    GROUP BY user_id
                ) ur ON ur.user_id = u.id
                LEFT JOIN roles r ON r.id = ur.role_id
                WHERE u.id = ?
                """,
                (user_id,)
            ).fetchone()
        return row

    # 验证用户名和密码的方法
    @staticmethod
    def verify_user(username: str, password: str) -> bool:
        row = UserRepository.get_user_by_username(username)

        if not row:
            return False

        salt = bytes.fromhex(row["salt"])

        return _hash_password(password, salt) == row["password_hash"]

    # 分页获取用户列表
    @staticmethod
    def get_user_list(page: int = 1, page_size: int = 20, username: str = None, status: int = None):
        offset = (page - 1) * page_size
        
        with get_connection() as conn:
            base_select = """
                SELECT u.id, u.username, u.nickname, u.email, u.role, u.status, u.last_login_at, u.create_at,
                       r.id AS role_id, r.name AS role_code, r.display_name AS role_name
                FROM users u
                LEFT JOIN (
                    SELECT user_id, MIN(role_id) AS role_id
                    FROM user_roles
                    GROUP BY user_id
                ) ur ON ur.user_id = u.id
                LEFT JOIN roles r ON r.id = ur.role_id
            """
            where_clauses = []
            params = []

            if username:
                where_clauses.append("u.username LIKE ?")
                params.append(f"%{username}%")

            if status is not None:
                where_clauses.append("u.status = ?")
                params.append(status)

            where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            rows = conn.execute(
                base_select + where_sql + " ORDER BY u.id DESC LIMIT ? OFFSET ?",
                params + [page_size, offset]
            ).fetchall()

            total = conn.execute(
                "SELECT COUNT(*) FROM users u" + where_sql,
                params
            ).fetchone()[0]
        
        return {
            "list": [dict(row) for row in rows],
            "total": total
        }

    # 更新用户信息
    @staticmethod
    def update_user(user_id: int, username: str = None, password: str = None, status: int = None, role_id: int = None, nickname: str = None, email: str = None) -> bool:
        with get_connection() as conn:
            current = conn.execute(
                "select username, nickname, email, status from users where id = ?",
                (user_id,)
            ).fetchone()
            
            if not current:
                return False
            
            new_username = username if username else current["username"]
            new_nickname = nickname if nickname is not None else current["nickname"]
            new_email = email if email is not None else current["email"]
            new_status = status if status is not None else current["status"]
            
            if password:
                salt = secrets.token_bytes(16)
                password_hash = _hash_password(password, salt)
                conn.execute(
                    "update users set username = ?, nickname = ?, email = ?, password_hash = ?, salt = ?, status = ? where id = ?",
                    (new_username, new_nickname, new_email, password_hash, salt.hex(), new_status, user_id)
                )
            else:
                conn.execute(
                    "update users set username = ?, nickname = ?, email = ?, status = ? where id = ?",
                    (new_username, new_nickname, new_email, new_status, user_id)
                )
            if role_id is not None:
                if not UserRepository._set_user_role(conn, user_id, role_id):
                    return False
            return True

    @staticmethod
    def update_last_login(username: str) -> bool:
        with get_connection() as conn:
            cursor = conn.execute(
                "UPDATE users SET last_login_at = datetime('now') WHERE username = ?",
                (username,)
            )
            return cursor.rowcount > 0

    @staticmethod
    def ensure_user_role(username: str, role_name: str) -> bool:
        with get_connection() as conn:
            user = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,)
            ).fetchone()
            role = UserRepository._get_role_by_name(conn, role_name)

            if not user or not role:
                return False

            return UserRepository._set_user_role(conn, user["id"], role["id"])

    # 删除用户
    @staticmethod
    def delete_user(user_id: int) -> bool:
        with get_connection() as conn:
            conn.execute("delete from user_roles where user_id = ?", (user_id,))
            cursor = conn.execute("delete from users where id = ?", (user_id,))
            return cursor.rowcount > 0

    # 批量删除用户
    @staticmethod
    def batch_delete_user(user_ids: list) -> int:
        if not user_ids:
            return 0

        with get_connection() as conn:
            placeholders = ",".join("?" for _ in user_ids)
            conn.execute(f"delete from user_roles where user_id in ({placeholders})", user_ids)
            cursor = conn.execute(f"delete from users where id in ({placeholders})", user_ids)
            return cursor.rowcount

    # 获取用户统计
    @staticmethod
    def get_user_count() -> int:
        with get_connection() as conn:
            return conn.execute("select count(*) from users").fetchone()[0]
