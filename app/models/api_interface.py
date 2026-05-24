import math

from app.models.db import get_connection


class ApiInterfaceRepository:
    @staticmethod
    def get_interface_by_id(interface_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM api_interfaces WHERE id = ?",
                (interface_id,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_enabled_interfaces():
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM api_interfaces WHERE status = 1 ORDER BY id DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_interface_list(page=1, page_size=20, keyword=None, status=None):
        offset = (page - 1) * page_size
        where = []
        params = []

        if keyword:
            where.append("(name LIKE ? OR endpoint_url LIKE ? OR category LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        if status is not None:
            where.append("status = ?")
            params.append(status)

        where_sql = " WHERE " + " AND ".join(where) if where else ""

        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM api_interfaces" + where_sql + " ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [page_size, offset]
            ).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) FROM api_interfaces" + where_sql,
                params
            ).fetchone()[0]

        return {
            "list": [dict(row) for row in rows],
            "total": total,
            "pages": math.ceil(total / page_size) if page_size else 0
        }
