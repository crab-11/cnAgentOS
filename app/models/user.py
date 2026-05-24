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
    # 创建用户方法
    @staticmethod
    def create_user(username: str, password: str, role: str = "user", status: int = 1) -> bool:
        salt = secrets.token_bytes(16)
        password_hash = _hash_password(password, salt)

        try:
            with get_connection() as conn:
                conn.execute(
                    "insert into users(username, password_hash, salt, role, status) values(?, ?, ?, ?, ?)",
                    (username, password_hash, salt.hex(), role, status)
                )
            return True
        except sqlite3.IntegrityError:
            return False

    # 通过用户名检索用户信息
    @staticmethod
    def get_user_by_username(username: str):
        with get_connection() as conn:
            row = conn.execute(
                "select id, username, password_hash, salt, role, status from users where username = ?",
                (username,)
            ).fetchone()
        return row

    # 通过ID获取用户
    @staticmethod
    def get_user_by_id(user_id: int):
        with get_connection() as conn:
            row = conn.execute(
                "select id, username, role, status, create_at from users where id = ?",
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
    def get_user_list(page: int = 1, page_size: int = 20, username: str = None):
        offset = (page - 1) * page_size
        
        with get_connection() as conn:
            if username:
                rows = conn.execute(
                    "select id, username, role, status, create_at from users where username like ? order by id desc limit ? offset ?",
                    (f"%{username}%", page_size, offset)
                ).fetchall()
                
                total = conn.execute(
                    "select count(*) from users where username like ?",
                    (f"%{username}%",)
                ).fetchone()[0]
            else:
                rows = conn.execute(
                    "select id, username, role, status, create_at from users order by id desc limit ? offset ?",
                    (page_size, offset)
                ).fetchall()
                
                total = conn.execute("select count(*) from users").fetchone()[0]
        
        return {
            "list": [dict(row) for row in rows],
            "total": total
        }

    # 更新用户信息
    @staticmethod
    def update_user(user_id: int, username: str = None, password: str = None, status: int = None) -> bool:
        with get_connection() as conn:
            current = conn.execute(
                "select username, status from users where id = ?",
                (user_id,)
            ).fetchone()
            
            if not current:
                return False
            
            new_username = username if username else current["username"]
            new_status = status if status is not None else current["status"]
            
            if password:
                salt = secrets.token_bytes(16)
                password_hash = _hash_password(password, salt)
                conn.execute(
                    "update users set username = ?, password_hash = ?, salt = ?, status = ? where id = ?",
                    (new_username, password_hash, salt.hex(), new_status, user_id)
                )
            else:
                conn.execute(
                    "update users set username = ?, status = ? where id = ?",
                    (new_username, new_status, user_id)
                )
            return True

    # 删除用户
    @staticmethod
    def delete_user(user_id: int) -> bool:
        with get_connection() as conn:
            cursor = conn.execute("delete from users where id = ?", (user_id,))
            return cursor.rowcount > 0

    # 批量删除用户
    @staticmethod
    def batch_delete_user(user_ids: list) -> int:
        with get_connection() as conn:
            placeholders = ",".join("?" for _ in user_ids)
            cursor = conn.execute(f"delete from users where id in ({placeholders})", user_ids)
            return cursor.rowcount

    # 获取用户统计
    @staticmethod
    def get_user_count() -> int:
        with get_connection() as conn:
            return conn.execute("select count(*) from users").fetchone()[0]
