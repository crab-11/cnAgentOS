from app.models.db import get_connection


class RoleRepository:
    @staticmethod
    def get_all_roles():
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM roles ORDER BY is_system DESC, id ASC"
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_role_by_id(role_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM roles WHERE id = ?",
                (role_id,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_role_by_name(name):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM roles WHERE name = ?",
                (name,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_role_list(page=1, page_size=20, name=None):
        offset = (page - 1) * page_size

        with get_connection() as conn:
            if name:
                rows = conn.execute(
                    "SELECT * FROM roles WHERE name LIKE ? OR display_name LIKE ? ORDER BY is_system DESC, id ASC LIMIT ? OFFSET ?",
                    (f"%{name}%", f"%{name}%", page_size, offset)
                ).fetchall()
                total = conn.execute(
                    "SELECT COUNT(*) FROM roles WHERE name LIKE ? OR display_name LIKE ?",
                    (f"%{name}%", f"%{name}%")
                ).fetchone()[0]
            else:
                rows = conn.execute(
                    "SELECT * FROM roles ORDER BY is_system DESC, id ASC LIMIT ? OFFSET ?",
                    (page_size, offset)
                ).fetchall()
                total = conn.execute("SELECT COUNT(*) FROM roles").fetchone()[0]

        return {
            "list": [dict(row) for row in rows],
            "total": total
        }

    @staticmethod
    def create_role(name, display_name, description=None):
        try:
            with get_connection() as conn:
                conn.execute(
                    """INSERT INTO roles(name, display_name, description, is_system, status)
                       VALUES(?, ?, ?, 0, 1)""",
                    (name, display_name, description)
                )
            return True
        except Exception:
            return False

    @staticmethod
    def update_role(role_id, display_name=None, description=None, status=None):
        updates = []
        params = []

        if display_name is not None:
            updates.append("display_name = ?")
            params.append(display_name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if status is not None:
            updates.append("status = ?")
            params.append(status)

        if not updates:
            return False

        params.append(role_id)

        with get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE roles SET {', '.join(updates)} WHERE id = ? AND is_system = 0",
                params
            )
            return cursor.rowcount > 0

    @staticmethod
    def delete_role(role_id):
        with get_connection() as conn:
            role = conn.execute(
                "SELECT id FROM roles WHERE id = ? AND is_system = 0",
                (role_id,)
            ).fetchone()

            if not role:
                return False

            conn.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_id,))
            conn.execute("DELETE FROM user_roles WHERE role_id = ?", (role_id,))
            cursor = conn.execute(
                "DELETE FROM roles WHERE id = ?",
                (role_id,)
            )
            return cursor.rowcount > 0

    @staticmethod
    def get_role_permissions(role_id):
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT p.* FROM permissions p
                   INNER JOIN role_permissions rp ON p.id = rp.permission_id
                   WHERE rp.role_id = ?
                   ORDER BY p.sort_order ASC""",
                (role_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def set_role_permissions(role_id, permission_ids):
        permission_ids = list(dict.fromkeys(permission_ids))

        with get_connection() as conn:
            conn.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_id,))

            for perm_id in permission_ids:
                conn.execute(
                    "INSERT INTO role_permissions(role_id, permission_id) VALUES(?, ?)",
                    (role_id, perm_id)
                )

        return True

    @staticmethod
    def get_role_count():
        with get_connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM roles").fetchone()[0]
