import hashlib
import ipaddress
import json
import re
import socket
import sqlite3
import urllib.parse
import xml.etree.ElementTree as ET
from html import unescape

import tornado.escape
import tornado.httpclient

from app.models.db import get_connection


class LookoutSourceRepository:
    @staticmethod
    def get_source_by_id(source_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM lookout_sources WHERE id = ?",
                (source_id,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_source_list(page=1, page_size=20, keyword=None, status=None):
        offset = (page - 1) * page_size
        where = []
        params = []

        if keyword:
            where.append("(name LIKE ? OR target_url LIKE ? OR keywords LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        if status is not None:
            where.append("status = ?")
            params.append(status)

        where_sql = " WHERE " + " AND ".join(where) if where else ""

        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT ls.*,
                       COALESCE(task_stats.task_count, 0) AS task_count,
                       COALESCE(task_stats.success_count, 0) AS success_count,
                       COALESCE(record_stats.record_count, 0) AS record_count
                FROM lookout_sources ls
                LEFT JOIN (
                    SELECT source_id,
                           COUNT(*) AS task_count,
                           SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_count
                    FROM lookout_tasks
                    GROUP BY source_id
                ) task_stats ON task_stats.source_id = ls.id
                LEFT JOIN (
                    SELECT source_id, COUNT(*) AS record_count
                    FROM lookout_records
                    GROUP BY source_id
                ) record_stats ON record_stats.source_id = ls.id
                """
                + where_sql +
                """
                ORDER BY ls.id DESC
                LIMIT ? OFFSET ?
                """,
                params + [page_size, offset]
            ).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) FROM lookout_sources" + where_sql,
                params
            ).fetchone()[0]

        return {
            "list": [dict(row) for row in rows],
            "total": total
        }

    @staticmethod
    def create_source(name, source_type, target_url, parser_type, keywords=None, status=1, remark=None):
        try:
            with get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO lookout_sources(
                        name, source_type, target_url, parser_type, keywords, status, remark
                    ) VALUES(?, ?, ?, ?, ?, ?, ?)
                    """,
                    (name, source_type, target_url, parser_type, keywords, status, remark)
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    @staticmethod
    def update_source(source_id, name, source_type, target_url, parser_type, keywords=None, status=1, remark=None):
        try:
            with get_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE lookout_sources
                    SET name = ?,
                        source_type = ?,
                        target_url = ?,
                        parser_type = ?,
                        keywords = ?,
                        status = ?,
                        remark = ?,
                        update_at = datetime('now')
                    WHERE id = ?
                    """,
                    (name, source_type, target_url, parser_type, keywords, status, remark, source_id)
                )
                return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            return False

    @staticmethod
    def delete_source(source_id):
        with get_connection() as conn:
            cursor = conn.execute("DELETE FROM lookout_sources WHERE id = ?", (source_id,))
            return cursor.rowcount > 0

    @staticmethod
    def update_last_collected_at(source_id):
        with get_connection() as conn:
            conn.execute(
                "UPDATE lookout_sources SET last_collected_at = datetime('now'), update_at = datetime('now') WHERE id = ?",
                (source_id,)
            )


class LookoutRecordRepository:
    @staticmethod
    def add_records(source_id, items):
        stored_count = 0
        with get_connection() as conn:
            for item in items:
                content_hash = _build_record_hash(item)
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO lookout_records(
                        source_id, title, summary, content_url, published_at, raw_payload, content_hash
                    ) VALUES(?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_id,
                        item.get("title") or "未命名内容",
                        item.get("summary"),
                        item.get("content_url"),
                        item.get("published_at"),
                        json.dumps(item.get("raw_payload"), ensure_ascii=False) if item.get("raw_payload") is not None else None,
                        content_hash
                    )
                )
                stored_count += cursor.rowcount
        return stored_count

    @staticmethod
    def get_record_list(page=1, page_size=20, keyword=None, source_id=None):
        offset = (page - 1) * page_size
        where = []
        params = []

        if keyword:
            where.append("(lr.title LIKE ? OR lr.summary LIKE ? OR ls.name LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        if source_id:
            where.append("lr.source_id = ?")
            params.append(source_id)

        where_sql = " WHERE " + " AND ".join(where) if where else ""

        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT lr.*, ls.name AS source_name
                FROM lookout_records lr
                INNER JOIN lookout_sources ls ON ls.id = lr.source_id
                """
                + where_sql +
                """
                ORDER BY lr.id DESC
                LIMIT ? OFFSET ?
                """,
                params + [page_size, offset]
            ).fetchall()
            total = conn.execute(
                """
                SELECT COUNT(*)
                FROM lookout_records lr
                INNER JOIN lookout_sources ls ON ls.id = lr.source_id
                """
                + where_sql,
                params
            ).fetchone()[0]

        return {
            "list": [dict(row) for row in rows],
            "total": total
        }


class LookoutTaskRepository:
    @staticmethod
    def create_task(source_id, source_name):
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO lookout_tasks(source_id, source_name, status)
                VALUES(?, ?, 'running')
                """,
                (source_id, source_name)
            )
            return cursor.lastrowid

    @staticmethod
    def finish_task(task_id, status, fetched_count=0, stored_count=0, error_message=None):
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE lookout_tasks
                SET status = ?,
                    fetched_count = ?,
                    stored_count = ?,
                    error_message = ?,
                    finish_at = datetime('now')
                WHERE id = ?
                """,
                (status, fetched_count, stored_count, error_message, task_id)
            )

    @staticmethod
    def get_task_list(page=1, page_size=20, source_id=None):
        offset = (page - 1) * page_size
        where_sql = " WHERE source_id = ?" if source_id else ""
        params = [source_id] if source_id else []

        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM lookout_tasks" + where_sql + " ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [page_size, offset]
            ).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) FROM lookout_tasks" + where_sql,
                params
            ).fetchone()[0]

        return {
            "list": [dict(row) for row in rows],
            "total": total
        }


class LookoutCollector:
    @staticmethod
    async def collect_source(source):
        _validate_target_url(source["target_url"])
        client = tornado.httpclient.AsyncHTTPClient()
        response = await client.fetch(
            tornado.httpclient.HTTPRequest(
                url=source["target_url"],
                method="GET",
                request_timeout=30,
                validate_cert=True,
                headers={"User-Agent": "cnAgentOS Lookout Bot/1.0"}
            )
        )
        body = response.body or b""
        content_type = response.headers.get("Content-Type", "")
        text = body.decode("utf-8", errors="ignore")

        parser_type = (source.get("parser_type") or "html").lower()
        if parser_type == "rss":
            items = _parse_rss(text)
        elif parser_type == "json":
            items = _parse_json(text)
        else:
            items = _parse_html(source["target_url"], text, content_type)

        return _filter_items_by_keywords(items, source.get("keywords"))


def _build_record_hash(item):
    raw = "|".join([
        item.get("title") or "",
        item.get("content_url") or "",
        item.get("published_at") or "",
        item.get("summary") or ""
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _validate_target_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("采集地址必须以 http:// 或 https:// 开头")
    if not parsed.hostname:
        raise ValueError("采集地址缺少主机名")

    try:
        host_ip = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        try:
            infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
        except socket.gaierror as e:
            raise ValueError(f"无法解析采集地址：{e}") from e
        for info in infos:
            ip_text = info[4][0]
            ip_obj = ipaddress.ip_address(ip_text)
            if _is_private_ip(ip_obj):
                raise ValueError("禁止访问内网或本地地址")
    else:
        if _is_private_ip(host_ip):
            raise ValueError("禁止访问内网或本地地址")


def _is_private_ip(ip_obj):
    return (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
    )


def _parse_rss(text):
    root = ET.fromstring(text)
    items = []
    for item in root.findall(".//item"):
        items.append({
            "title": _safe_xml_text(item.find("title")) or "未命名RSS条目",
            "summary": _strip_html(_safe_xml_text(item.find("description")) or ""),
            "content_url": _safe_xml_text(item.find("link")),
            "published_at": _safe_xml_text(item.find("pubDate")),
            "raw_payload": {
                "title": _safe_xml_text(item.find("title")),
                "link": _safe_xml_text(item.find("link")),
                "description": _safe_xml_text(item.find("description")),
                "pubDate": _safe_xml_text(item.find("pubDate"))
            }
        })
    return items


def _parse_json(text):
    data = json.loads(text)
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get("items") or data.get("data") or data.get("list") or [data]
    else:
        rows = []

    items = []
    for row in rows[:100]:
        if not isinstance(row, dict):
            continue
        items.append({
            "title": str(row.get("title") or row.get("name") or row.get("subject") or "未命名JSON条目"),
            "summary": str(row.get("summary") or row.get("description") or row.get("content") or "")[:500],
            "content_url": row.get("url") or row.get("link"),
            "published_at": row.get("published_at") or row.get("pubDate") or row.get("date"),
            "raw_payload": row
        })
    return items


def _parse_html(page_url, text, content_type):
    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    title = _strip_html(title_match.group(1)) if title_match else page_url

    desc_match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        text,
        re.IGNORECASE | re.DOTALL
    )
    summary = _strip_html(desc_match.group(1)) if desc_match else _strip_html(text)[:240]

    return [{
        "title": title or page_url,
        "summary": summary,
        "content_url": page_url,
        "published_at": None,
        "raw_payload": {
            "content_type": content_type,
            "html_excerpt": text[:2000]
        }
    }]


def _filter_items_by_keywords(items, keywords):
    keyword_list = [item.strip().lower() for item in (keywords or "").split(",") if item.strip()]
    if not keyword_list:
        return items

    matched = []
    for item in items:
        haystack = " ".join([
            str(item.get("title") or ""),
            str(item.get("summary") or "")
        ]).lower()
        if any(keyword in haystack for keyword in keyword_list):
            matched.append(item)
    return matched


def _safe_xml_text(node):
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _strip_html(text):
    clean = re.sub(r"<[^>]+>", " ", text or "")
    clean = unescape(clean)
    clean = tornado.escape.squeeze(clean)
    return clean.strip()
