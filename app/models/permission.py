from app.models.db import get_connection


class PermissionRepository:
    @staticmethod
    def get_all_permissions():
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM permissions ORDER BY sort_order ASC, id ASC"
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_permission_by_id(permission_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM permissions WHERE id = ?",
                (permission_id,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_permission_list(page=1, page_size=50, name=None, category=None):
        offset = (page - 1) * page_size

        with get_connection() as conn:
            where_clauses = []
            params = []

            if name:
                where_clauses.append("(name LIKE ? OR display_name LIKE ?)")
                params.extend([f"%{name}%", f"%{name}%"])

            if category:
                where_clauses.append("category = ?")
                params.append(category)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            sql = f"SELECT * FROM permissions WHERE {where_sql} ORDER BY sort_order ASC, id ASC LIMIT ? OFFSET ?"
            rows = conn.execute(sql, params + [page_size, offset]).fetchall()

            count_sql = f"SELECT COUNT(*) FROM permissions WHERE {where_sql}"
            total = conn.execute(count_sql, params).fetchone()[0]

        return {
            "list": [dict(row) for row in rows],
            "total": total
        }

    @staticmethod
    def create_permission(name, display_name, code, category="menu", parent_id=0, icon=None, url=None, sort_order=0):
        try:
            with get_connection() as conn:
                conn.execute(
                    """INSERT INTO permissions(name, display_name, code, category, parent_id, icon, url, sort_order)
                       VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
                    (name, display_name, code, category, parent_id, icon, url, sort_order)
                )
            return True
        except Exception:
            return False

    @staticmethod
    def update_permission(permission_id, name=None, display_name=None, code=None, category=None, parent_id=None, icon=None, url=None, sort_order=None, status=None):
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if display_name is not None:
            updates.append("display_name = ?")
            params.append(display_name)
        if code is not None:
            updates.append("code = ?")
            params.append(code)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if parent_id is not None:
            updates.append("parent_id = ?")
            params.append(parent_id)
        if icon is not None:
            updates.append("icon = ?")
            params.append(icon)
        if url is not None:
            updates.append("url = ?")
            params.append(url)
        if sort_order is not None:
            updates.append("sort_order = ?")
            params.append(sort_order)
        if status is not None:
            updates.append("status = ?")
            params.append(status)

        if not updates:
            return False

        params.append(permission_id)

        with get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE permissions SET {', '.join(updates)} WHERE id = ?",
                params
            )
            return cursor.rowcount > 0

    @staticmethod
    def delete_permission(permission_id):
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id FROM permissions WHERE id = ? OR parent_id = ?",
                (permission_id, permission_id)
            ).fetchall()
            permission_ids = [row["id"] for row in rows]

            if not permission_ids:
                return False

            placeholders = ",".join("?" for _ in permission_ids)
            conn.execute(
                f"DELETE FROM role_permissions WHERE permission_id IN ({placeholders})",
                permission_ids
            )
            cursor = conn.execute(
                f"DELETE FROM permissions WHERE id IN ({placeholders})",
                permission_ids
            )
            return cursor.rowcount > 0

    @staticmethod
    def get_categories():
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT category FROM permissions WHERE category != 'group' ORDER BY category"
            ).fetchall()
        return [row[0] for row in rows]

    @staticmethod
    def get_permission_tree():
        permissions = PermissionRepository.get_all_permissions()

        groups = []
        menus = []

        for p in permissions:
            if p['category'] == 'group':
                groups.append(p)
            else:
                menus.append(p)

        for group in groups:
            group['children'] = [m for m in menus if m['parent_id'] == group['id']]

        return groups

    @staticmethod
    def get_menus_by_parent(parent_id=0):
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM permissions WHERE category != 'group' AND parent_id = ? ORDER BY sort_order ASC",
                (parent_id,)
            ).fetchall()
        return [dict(row) for row in rows]
