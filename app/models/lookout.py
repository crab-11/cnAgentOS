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
        return _row_to_source(row)

    @staticmethod
    def get_enabled_sources():
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM lookout_sources WHERE status = 1 ORDER BY id DESC"
            ).fetchall()
        return [_row_to_source(row) for row in rows]

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
            "list": [_row_to_source(row) | {
                "task_count": row["task_count"],
                "success_count": row["success_count"],
                "record_count": row["record_count"]
            } for row in rows],
            "total": total
        }

    @staticmethod
    def create_source(name, source_type, target_url, request_method, parser_type,
                      request_headers=None, default_params=None, param_config=None,
                      extract_rules=None, page_param="pn", page_step=10,
                      keyword_param="word", keywords=None, status=1, remark=None):
        try:
            with get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO lookout_sources(
                        name, source_type, target_url, request_method, parser_type,
                        request_headers, default_params, param_config, extract_rules,
                        page_param, page_step, keyword_param, keywords, status, remark
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name, source_type, target_url, request_method, parser_type,
                        request_headers, default_params, param_config, extract_rules,
                        page_param, page_step, keyword_param, keywords, status, remark
                    )
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    @staticmethod
    def update_source(source_id, name, source_type, target_url, request_method, parser_type,
                      request_headers=None, default_params=None, param_config=None,
                      extract_rules=None, page_param="pn", page_step=10,
                      keyword_param="word", keywords=None, status=1, remark=None):
        try:
            with get_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE lookout_sources
                    SET name = ?,
                        source_type = ?,
                        target_url = ?,
                        request_method = ?,
                        parser_type = ?,
                        request_headers = ?,
                        default_params = ?,
                        param_config = ?,
                        extract_rules = ?,
                        page_param = ?,
                        page_step = ?,
                        keyword_param = ?,
                        keywords = ?,
                        status = ?,
                        remark = ?,
                        update_at = datetime('now')
                    WHERE id = ?
                    """,
                    (
                        name, source_type, target_url, request_method, parser_type,
                        request_headers, default_params, param_config, extract_rules,
                        page_param, page_step, keyword_param, keywords, status, remark, source_id
                    )
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
    def add_records(source_id, keyword, items):
        stored_count = 0
        with get_connection() as conn:
            for item in items:
                content_hash = _build_record_hash(item)
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO lookout_records(
                        source_id, keyword, title, summary, content_url, source_page_url,
                        published_at, raw_payload, content_hash
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_id,
                        keyword,
                        item.get("title") or "未命名内容",
                        item.get("summary"),
                        item.get("content_url"),
                        item.get("source_page_url"),
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
            where.append("(lr.title LIKE ? OR lr.summary LIKE ? OR ls.name LIKE ? OR lr.keyword LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
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

    @staticmethod
    def delete_record(record_id):
        with get_connection() as conn:
            cursor = conn.execute("DELETE FROM lookout_records WHERE id = ?", (record_id,))
            return cursor.rowcount > 0

    @staticmethod
    def batch_delete(record_ids):
        if not record_ids:
            return 0
        placeholders = ",".join("?" for _ in record_ids)
        with get_connection() as conn:
            cursor = conn.execute(
                f"DELETE FROM lookout_records WHERE id IN ({placeholders})",
                record_ids
            )
            return cursor.rowcount


class LookoutTaskRepository:
    @staticmethod
    def create_task(source_id, source_name, keyword=None, page_count=1, page_size=20):
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO lookout_tasks(source_id, source_name, keyword, page_count, page_size, status)
                VALUES(?, ?, ?, ?, ?, 'running')
                """,
                (source_id, source_name, keyword, page_count, page_size)
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
    async def collect_source(source, keyword=None, page_count=1, page_size=20):
        page_count = max(1, int(page_count or 1))
        page_size = max(1, int(page_size or 20))
        headers = _parse_json_object(source.get("request_headers"))
        default_params = _parse_json_object(source.get("default_params"))
        extract_rules = _parse_json_object(source.get("extract_rules"))

        parser_type = (source.get("parser_type") or "html").lower()
        page_step = int(source.get("page_step") or 10)
        page_param = source.get("page_param") or "pn"
        keyword_param = source.get("keyword_param") or "word"
        request_method = (source.get("request_method") or "GET").upper()

        results = []
        client = tornado.httpclient.AsyncHTTPClient()

        for page_index in range(page_count):
            runtime_params = dict(default_params)
            if keyword:
                runtime_params[keyword_param] = keyword
            runtime_params[page_param] = page_index * page_step

            page_url = _build_request_url(source["target_url"], runtime_params)
            _validate_target_url(page_url)

            request = tornado.httpclient.HTTPRequest(
                url=page_url,
                method=request_method,
                request_timeout=40,
                validate_cert=True,
                headers=headers or {"User-Agent": "cnAgentOS Lookout Bot/1.0"}
            )
            response = await client.fetch(request)
            body = response.body or b""
            content_type = response.headers.get("Content-Type", "")
            text = body.decode("utf-8", errors="ignore")

            if parser_type == "rss":
                items = _parse_rss(text, page_url)
            elif parser_type == "json":
                items = _parse_json(text, page_url)
            elif parser_type == "baidu_news":
                items = _parse_baidu_news_search(text, page_url, keyword, extract_rules)
            else:
                items = _parse_html(page_url, text, content_type)

            items = _filter_items_by_keywords(items, source.get("keywords"))
            for item in items:
                item.setdefault("source_page_url", page_url)
            results.extend(items)
            if len(results) >= page_size:
                break

        return results[:page_size]


def _row_to_source(row):
    return dict(row) if row else None


def _parse_json_object(text):
    if not text:
        return {}
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _build_record_hash(item):
    raw = "|".join([
        item.get("title") or "",
        item.get("content_url") or "",
        item.get("published_at") or "",
        item.get("summary") or ""
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _build_request_url(target_url, params):
    rendered = target_url
    used_keys = set()
    for key, value in params.items():
        token = "{" + str(key) + "}"
        if token in rendered:
            rendered = rendered.replace(token, urllib.parse.quote_plus(str(value)))
            used_keys.add(key)

    remaining_params = {k: v for k, v in params.items() if k not in used_keys}
    if not remaining_params:
        return rendered

    parsed = urllib.parse.urlparse(rendered)
    current_query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    current_query.update({str(k): str(v) for k, v in remaining_params.items()})
    new_query = urllib.parse.urlencode(current_query)
    return urllib.parse.urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))


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


def _parse_rss(text, page_url):
    root = ET.fromstring(text)
    items = []
    for item in root.findall(".//item"):
        items.append({
            "title": _safe_xml_text(item.find("title")) or "未命名RSS条目",
            "summary": _strip_html(_safe_xml_text(item.find("description")) or ""),
            "content_url": _safe_xml_text(item.find("link")),
            "source_page_url": page_url,
            "published_at": _safe_xml_text(item.find("pubDate")),
            "raw_payload": {
                "title": _safe_xml_text(item.find("title")),
                "link": _safe_xml_text(item.find("link")),
                "description": _safe_xml_text(item.find("description")),
                "pubDate": _safe_xml_text(item.find("pubDate"))
            }
        })
    return items


def _parse_json(text, page_url):
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
            "source_page_url": page_url,
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
        "source_page_url": page_url,
        "published_at": None,
        "raw_payload": {
            "content_type": content_type,
            "html_excerpt": text[:2000]
        }
    }]


def _parse_baidu_news_search(text, page_url, keyword, extract_rules):
    summary_window = int(extract_rules.get("summary_window") or 420)
    link_attr_priority = extract_rules.get("link_attr_priority") or ["data-landurl", "mu", "href"]
    anchor_pattern = re.compile(r"<a\b([^>]+)>(.*?)</a>", re.IGNORECASE | re.DOTALL)
    items = []
    seen = set()

    for match in anchor_pattern.finditer(text):
        attrs = match.group(1)
        raw_title = match.group(2)
        title = _strip_html(raw_title)
        if not title or len(title) < 6:
            continue
        if keyword and keyword not in title and keyword not in _strip_html(match.group(0)):
            continue
        if any(skip in title for skip in ("百度", "上一页", "下一页", "更多", "打开APP", "投诉")):
            continue

        url = None
        for attr_name in link_attr_priority:
            attr_match = re.search(rf'{attr_name}=["\'](.*?)["\']', attrs, re.IGNORECASE | re.DOTALL)
            if attr_match and attr_match.group(1).strip():
                url = unescape(attr_match.group(1).strip())
                break
        if not url:
            continue
        if url.startswith("/"):
            url = urllib.parse.urljoin(page_url, url)

        block = text[match.end():match.end() + summary_window]
        block_text = _strip_html(block)
        summary = block_text[:220] if block_text else ""
        published_at = _extract_datetime(block_text)
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        items.append({
            "title": title,
            "summary": summary,
            "content_url": url,
            "source_page_url": page_url,
            "published_at": published_at,
            "raw_payload": {
                "anchor_attrs": attrs,
                "anchor_html": match.group(0),
                "summary_excerpt": block[:summary_window]
            }
        })

    return items


def _extract_datetime(text):
    patterns = [
        r"\d{4}-\d{1,2}-\d{1,2}(?:\s+\d{1,2}:\d{1,2})?",
        r"\d{4}/\d{1,2}/\d{1,2}(?:\s+\d{1,2}:\d{1,2})?",
        r"\d{1,2}月\d{1,2}日(?:\s+\d{1,2}:\d{1,2})?",
        r"\d+\s*小时前",
        r"\d+\s*分钟前"
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None


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
