import math
from app.models.db import get_connection


class ModelServiceRepository:
    @staticmethod
    def _row_to_dict(row):
        return dict(row) if row else None

    @staticmethod
    def _mask_key(api_key):
        if not api_key:
            return ""
        if len(api_key) <= 10:
            return api_key[:2] + "****"
        return api_key[:6] + "****" + api_key[-4:]

    @staticmethod
    def get_service_by_id(service_id, include_secret=False):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM model_services WHERE id = ?",
                (service_id,)
            ).fetchone()
        item = ModelServiceRepository._row_to_dict(row)
        if item and not include_secret:
            item["api_key_masked"] = ModelServiceRepository._mask_key(item.get("api_key"))
            item.pop("api_key", None)
        return item

    @staticmethod
    def get_default_service():
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM model_services
                WHERE is_default = 1 AND status = 1
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        return ModelServiceRepository._row_to_dict(row)

    @staticmethod
    def get_service_list(page=1, page_size=6, keyword=None, status=None):
        offset = (page - 1) * page_size
        where = []
        params = []

        if keyword:
            where.append("(name LIKE ? OR provider LIKE ? OR model_name LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])

        if status is not None:
            where.append("status = ?")
            params.append(status)

        where_sql = " WHERE " + " AND ".join(where) if where else ""

        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT ms.*,
                       COALESCE(SUM(mcl.total_tokens), 0) AS total_tokens,
                       COALESCE(SUM(mcl.prompt_tokens), 0) AS prompt_tokens,
                       COALESCE(SUM(mcl.completion_tokens), 0) AS completion_tokens,
                       COUNT(mcl.id) AS call_count,
                       COALESCE(SUM(CASE WHEN mcl.success = 1 THEN 1 ELSE 0 END), 0) AS success_count
                FROM model_services ms
                LEFT JOIN model_call_logs mcl ON mcl.service_id = ms.id
                """
                + where_sql
                + """
                GROUP BY ms.id
                ORDER BY ms.is_default DESC, ms.id DESC
                LIMIT ? OFFSET ?
                """,
                params + [page_size, offset]
            ).fetchall()

            total = conn.execute(
                "SELECT COUNT(*) FROM model_services" + where_sql,
                params
            ).fetchone()[0]

        items = []
        for row in rows:
            item = dict(row)
            item["api_key_masked"] = ModelServiceRepository._mask_key(item.get("api_key"))
            item.pop("api_key", None)
            item["success_rate"] = 0
            if item["call_count"]:
                item["success_rate"] = round(item["success_count"] * 100 / item["call_count"], 1)
            items.append(item)

        return {
            "list": items,
            "total": total,
            "pages": math.ceil(total / page_size) if page_size else 0
        }

    @staticmethod
    def create_service(name, provider, endpoint_url, api_key, model_name,
                       temperature=0.7, max_tokens=1024, stream_enabled=1,
                       is_default=0, status=1, remark=None):
        with get_connection() as conn:
            if is_default:
                conn.execute("UPDATE model_services SET is_default = 0")
            cursor = conn.execute(
                """
                INSERT INTO model_services(
                    name, provider, endpoint_url, api_key, model_name,
                    temperature, max_tokens, stream_enabled, is_default,
                    status, remark
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name, provider, endpoint_url, api_key, model_name,
                    temperature, max_tokens, stream_enabled, is_default,
                    status, remark
                )
            )
            return cursor.lastrowid

    @staticmethod
    def update_service(service_id, name, provider, endpoint_url, api_key, model_name,
                       temperature=0.7, max_tokens=1024, stream_enabled=1,
                       is_default=0, status=1, remark=None):
        with get_connection() as conn:
            current = conn.execute(
                "SELECT id, api_key FROM model_services WHERE id = ?",
                (service_id,)
            ).fetchone()
            if not current:
                return False

            new_api_key = api_key if api_key else current["api_key"]
            if is_default:
                conn.execute("UPDATE model_services SET is_default = 0 WHERE id != ?", (service_id,))

            cursor = conn.execute(
                """
                UPDATE model_services
                SET name = ?,
                    provider = ?,
                    endpoint_url = ?,
                    api_key = ?,
                    model_name = ?,
                    temperature = ?,
                    max_tokens = ?,
                    stream_enabled = ?,
                    is_default = ?,
                    status = ?,
                    remark = ?,
                    update_at = datetime('now')
                WHERE id = ?
                """,
                (
                    name, provider, endpoint_url, new_api_key, model_name,
                    temperature, max_tokens, stream_enabled, is_default,
                    status, remark, service_id
                )
            )
            return cursor.rowcount > 0

    @staticmethod
    def delete_service(service_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM model_call_logs WHERE service_id = ?", (service_id,))
            cursor = conn.execute(
                "DELETE FROM model_services WHERE id = ?",
                (service_id,)
            )
            return cursor.rowcount > 0

    @staticmethod
    def set_default(service_id):
        with get_connection() as conn:
            service = conn.execute(
                "SELECT id FROM model_services WHERE id = ? AND status = 1",
                (service_id,)
            ).fetchone()
            if not service:
                return False
            conn.execute("UPDATE model_services SET is_default = 0")
            cursor = conn.execute(
                "UPDATE model_services SET is_default = 1, update_at = datetime('now') WHERE id = ?",
                (service_id,)
            )
            return cursor.rowcount > 0

    @staticmethod
    def record_call(service_id, model_name, prompt_tokens=0, completion_tokens=0,
                    total_tokens=0, latency_ms=0, success=1, error_message=None):
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO model_call_logs(
                    service_id, model_name, prompt_tokens, completion_tokens,
                    total_tokens, latency_ms, success, error_message
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    service_id, model_name, prompt_tokens, completion_tokens,
                    total_tokens, latency_ms, success, error_message
                )
            )
        return True

    @staticmethod
    def get_token_stats(service_id=None, days=7):
        params = []
        where = "WHERE mcl.create_at >= datetime('now', ?)"
        params.append(f"-{int(days)} days")
        if service_id:
            where += " AND mcl.service_id = ?"
            params.append(service_id)

        with get_connection() as conn:
            summary = conn.execute(
                f"""
                SELECT
                    COALESCE(SUM(total_tokens), 0) AS total_tokens,
                    COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                    COUNT(*) AS call_count,
                    COALESCE(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END), 0) AS success_count,
                    COALESCE(AVG(latency_ms), 0) AS avg_latency
                FROM model_call_logs mcl
                {where}
                """,
                params
            ).fetchone()
            daily_rows = conn.execute(
                f"""
                SELECT substr(mcl.create_at, 1, 10) AS day,
                       COALESCE(SUM(mcl.total_tokens), 0) AS total_tokens,
                       COUNT(*) AS call_count
                FROM model_call_logs mcl
                {where}
                GROUP BY substr(mcl.create_at, 1, 10)
                ORDER BY day ASC
                """,
                params
            ).fetchall()
            model_rows = conn.execute(
                f"""
                SELECT ms.name AS service_name,
                       mcl.model_name,
                       COALESCE(SUM(mcl.total_tokens), 0) AS total_tokens,
                       COUNT(*) AS call_count
                FROM model_call_logs mcl
                LEFT JOIN model_services ms ON ms.id = mcl.service_id
                {where}
                GROUP BY mcl.service_id, mcl.model_name
                ORDER BY total_tokens DESC
                LIMIT 6
                """,
                params
            ).fetchall()

        data = dict(summary)
        data["success_rate"] = 0
        if data["call_count"]:
            data["success_rate"] = round(data["success_count"] * 100 / data["call_count"], 1)
        data["avg_latency"] = int(data["avg_latency"] or 0)
        data["daily"] = [dict(row) for row in daily_rows]
        data["models"] = [dict(row) for row in model_rows]
        return data
