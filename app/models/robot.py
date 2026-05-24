import json
import math
import re
import time
import urllib.parse

import tornado.escape
import tornado.httpclient

from app.models.api_interface import ApiInterfaceRepository
from app.models.db import get_connection
from app.models.model_service import ModelServiceRepository


MENTION_PATTERN = re.compile(r"^\s*@(?P<alias>[^\s@]+)\s*(?P<query>.*)$")


class DigitalEmployeeRepository:
    @staticmethod
    def get_employee_by_id(employee_id):
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT de.*,
                       ms.name AS model_service_name,
                       ai.name AS api_interface_name
                FROM digital_employees de
                LEFT JOIN model_services ms ON ms.id = de.model_service_id
                LEFT JOIN api_interfaces ai ON ai.id = de.api_interface_id
                WHERE de.id = ?
                """,
                (employee_id,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_employee_by_alias(alias, enabled_only=True):
        with get_connection() as conn:
            sql = """
                SELECT de.*,
                       ms.name AS model_service_name,
                       ai.name AS api_interface_name
                FROM digital_employees de
                LEFT JOIN model_services ms ON ms.id = de.model_service_id
                LEFT JOIN api_interfaces ai ON ai.id = de.api_interface_id
                WHERE de.alias = ?
            """
            params = [alias]
            if enabled_only:
                sql += " AND de.status = 1"
            row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_employee_list(page=1, page_size=20, keyword=None, status=None, employee_type=None):
        offset = (page - 1) * page_size
        where = []
        params = []

        if keyword:
            where.append("(de.name LIKE ? OR de.alias LIKE ? OR de.description LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        if status is not None:
            where.append("de.status = ?")
            params.append(status)
        if employee_type:
            where.append("de.employee_type = ?")
            params.append(employee_type)

        where_sql = " WHERE " + " AND ".join(where) if where else ""

        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT de.*,
                       ms.name AS model_service_name,
                       ai.name AS api_interface_name
                FROM digital_employees de
                LEFT JOIN model_services ms ON ms.id = de.model_service_id
                LEFT JOIN api_interfaces ai ON ai.id = de.api_interface_id
                """
                + where_sql +
                """
                ORDER BY de.id DESC
                LIMIT ? OFFSET ?
                """,
                params + [page_size, offset]
            ).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) FROM digital_employees de" + where_sql,
                params
            ).fetchone()[0]

        return {
            "list": [dict(row) for row in rows],
            "total": total,
            "pages": math.ceil(total / page_size) if page_size else 0
        }

    @staticmethod
    def create_employee(name, alias, employee_type, service_type, description=None,
                        prompt_template=None, model_service_id=None, use_default_model=1,
                        api_interface_id=None, request_param_name=None, request_param_template=None,
                        response_mode="text", status=1, remark=None):
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO digital_employees(
                    name, alias, employee_type, service_type, description,
                    prompt_template, model_service_id, use_default_model,
                    api_interface_id, request_param_name, request_param_template,
                    response_mode, status, remark
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name, alias, employee_type, service_type, description,
                    prompt_template, model_service_id, use_default_model,
                    api_interface_id, request_param_name, request_param_template,
                    response_mode, status, remark
                )
            )
            return cursor.lastrowid

    @staticmethod
    def update_employee(employee_id, name, alias, employee_type, service_type, description=None,
                        prompt_template=None, model_service_id=None, use_default_model=1,
                        api_interface_id=None, request_param_name=None, request_param_template=None,
                        response_mode="text", status=1, remark=None):
        with get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE digital_employees
                SET name = ?,
                    alias = ?,
                    employee_type = ?,
                    service_type = ?,
                    description = ?,
                    prompt_template = ?,
                    model_service_id = ?,
                    use_default_model = ?,
                    api_interface_id = ?,
                    request_param_name = ?,
                    request_param_template = ?,
                    response_mode = ?,
                    status = ?,
                    remark = ?,
                    update_at = datetime('now')
                WHERE id = ?
                """,
                (
                    name, alias, employee_type, service_type, description,
                    prompt_template, model_service_id, use_default_model,
                    api_interface_id, request_param_name, request_param_template,
                    response_mode, status, remark, employee_id
                )
            )
            return cursor.rowcount > 0

    @staticmethod
    def delete_employee(employee_id):
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM digital_employees WHERE id = ?",
                (employee_id,)
            )
            return cursor.rowcount > 0

    @staticmethod
    def get_enabled_options():
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, alias, employee_type, service_type FROM digital_employees WHERE status = 1 ORDER BY id DESC"
            ).fetchall()
        return [dict(row) for row in rows]


class DigitalEmployeeService:
    @staticmethod
    def parse_message(message):
        match = MENTION_PATTERN.match((message or "").strip())
        if not match:
            return None
        return {
            "alias": match.group("alias").strip(),
            "query": (match.group("query") or "").strip()
        }

    @staticmethod
    async def invoke_from_message(message):
        parsed = DigitalEmployeeService.parse_message(message)
        if not parsed:
            raise ValueError("请使用 @别名 指令，例如：@天气 北京市")
        employee = DigitalEmployeeRepository.get_employee_by_alias(parsed["alias"])
        if not employee:
            raise ValueError(f"未找到名为 @{parsed['alias']} 的数字员工")
        return await DigitalEmployeeService.invoke_employee(employee, parsed["query"])

    @staticmethod
    async def invoke_employee(employee, query):
        if employee.get("service_type") == "model":
            return await DigitalEmployeeService._invoke_model_employee(employee, query)
        return await DigitalEmployeeService._invoke_api_employee(employee, query)

    @staticmethod
    async def stream_employee(employee, query, handler):
        if employee.get("service_type") == "model":
            return await DigitalEmployeeService._stream_model_employee(employee, query, handler)

        result = await DigitalEmployeeService._invoke_api_employee(employee, query)
        handler.write("event: result\n")
        handler.write("data: " + json.dumps(result, ensure_ascii=False) + "\n\n")
        handler.write("event: done\n")
        handler.write("data: [DONE]\n\n")
        await handler.flush()
        return result

    @staticmethod
    async def _invoke_model_employee(employee, query):
        service = _resolve_model_service(employee)
        prompt = _build_model_prompt(employee, query)
        start_time = time.time()
        response_data = await _call_openai_service(service, prompt, stream=False)
        content = _extract_content(response_data)
        latency_ms = int((time.time() - start_time) * 1000)
        prompt_tokens, completion_tokens, total_tokens = _extract_usage(response_data, prompt, content)
        ModelServiceRepository.record_call(
            service_id=service["id"],
            model_name=service["model_name"],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            success=1
        )
        return {
            "employee": _employee_brief(employee),
            "kind": "ai",
            "response_mode": employee.get("response_mode") or "sse",
            "content": content,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }

    @staticmethod
    async def _stream_model_employee(employee, query, handler):
        service = _resolve_model_service(employee)
        prompt = _build_model_prompt(employee, query)
        start_time = time.time()
        output = {"text": "", "buffer": ""}

        def on_chunk(chunk):
            text = chunk.decode("utf-8", errors="ignore")
            output["buffer"] += text
            while "\n" in output["buffer"]:
                line, output["buffer"] = output["buffer"].split("\n", 1)
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    continue
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                delta = _extract_stream_delta(data)
                if delta:
                    output["text"] += delta
                    handler.write("data: " + json.dumps({"delta": delta}, ensure_ascii=False) + "\n\n")
                    handler.flush()

        await _call_openai_service(service, prompt, stream=True, streaming_callback=on_chunk)
        latency_ms = int((time.time() - start_time) * 1000)
        prompt_tokens = _estimate_tokens(prompt)
        completion_tokens = _estimate_tokens(output["text"])
        total_tokens = prompt_tokens + completion_tokens
        ModelServiceRepository.record_call(
            service_id=service["id"],
            model_name=service["model_name"],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            success=1
        )
        handler.write("event: summary\n")
        handler.write("data: " + json.dumps({
            "employee": _employee_brief(employee),
            "kind": "ai",
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }, ensure_ascii=False) + "\n\n")
        handler.write("event: done\n")
        handler.write("data: [DONE]\n\n")
        await handler.flush()
        return output["text"]

    @staticmethod
    async def _invoke_api_employee(employee, query):
        api_interface = _resolve_api_interface(employee)
        request_data = _build_api_request(employee, api_interface, query)
        result = await _call_api_interface(api_interface, request_data)
        return {
            "employee": _employee_brief(employee),
            "kind": "api",
            "response_mode": employee.get("response_mode") or "json",
            "content": _summarize_api_response(employee, result, query),
            "raw": result,
            "card": _extract_card_payload(employee, result)
        }


def _employee_brief(employee):
    return {
        "id": employee.get("id"),
        "name": employee.get("name"),
        "alias": employee.get("alias"),
        "employee_type": employee.get("employee_type"),
        "service_type": employee.get("service_type")
    }


def _resolve_model_service(employee):
    service = None
    if int(employee.get("use_default_model") or 0) == 1:
        service = ModelServiceRepository.get_default_service()
    elif employee.get("model_service_id"):
        service = ModelServiceRepository.get_service_by_id(employee["model_service_id"], include_secret=True)
    if not service or service.get("status") != 1:
        raise RuntimeError("数字员工未绑定可用模型服务，请先在模型引擎中设置默认模型或绑定专属模型")
    return service


def _resolve_api_interface(employee):
    api_interface_id = employee.get("api_interface_id")
    if not api_interface_id:
        raise RuntimeError("数字员工未绑定 API 服务")
    api_interface = ApiInterfaceRepository.get_interface_by_id(api_interface_id)
    if not api_interface or int(api_interface.get("status") or 0) != 1:
        raise RuntimeError("绑定的 API 服务不存在或已禁用")
    return api_interface


def _build_model_prompt(employee, query):
    prompt = (employee.get("prompt_template") or "").strip()
    if not query:
        query = "请介绍一下你的能力。"
    if prompt:
        return prompt + "\n\n用户问题：" + query
    return query


def _build_api_request(employee, api_interface, query):
    params = _parse_json_object(api_interface.get("default_query_params"))
    template_params = _parse_json_object(_render_param_template(employee.get("request_param_template"), query))
    params.update(template_params)
    request_param_name = (employee.get("request_param_name") or "").strip()
    if request_param_name and query and request_param_name not in params:
        params[request_param_name] = query
    return {
        "method": (api_interface.get("request_method") or "GET").upper(),
        "url": api_interface.get("endpoint_url"),
        "params": params
    }


def _render_param_template(template_text, query):
    if not template_text:
        return ""
    return template_text.replace("{query}", query or "")


async def _call_api_interface(api_interface, request_data):
    method = request_data["method"]
    url = request_data["url"]
    params = request_data["params"] or {}
    body = None

    if method == "GET":
        if params:
            parsed = urllib.parse.urlparse(url)
            existing = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
            existing.update({str(k): str(v) for k, v in params.items() if v is not None})
            url = urllib.parse.urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                urllib.parse.urlencode(existing),
                parsed.fragment
            ))
    else:
        body = tornado.escape.json_encode(params)

    request = tornado.httpclient.HTTPRequest(
        url=url,
        method=method,
        headers={"Content-Type": "application/json"},
        body=body,
        request_timeout=30,
        validate_cert=True
    )
    client = tornado.httpclient.AsyncHTTPClient()
    response = await client.fetch(request, raise_error=False)
    if response.code < 200 or response.code >= 300:
        body_text = (response.body or b"").decode("utf-8", errors="ignore")
        raise RuntimeError(f"API 调用失败：HTTP {response.code} {body_text[:200]}")
    body_text = (response.body or b"{}").decode("utf-8", errors="ignore")
    try:
        return json.loads(body_text)
    except json.JSONDecodeError:
        return {"raw_text": body_text}


def _summarize_api_response(employee, result, query):
    if employee.get("alias") == "天气":
        city = query or _first_non_empty(result, ["city", "province", "location"]) or "目标城市"
        weather = _find_text_in_tree(result, ["weather", "type", "text", "tem_day", "tem1"])
        low = _find_text_in_tree(result, ["low", "tem2", "min"])
        high = _find_text_in_tree(result, ["high", "tem1", "max"])
        summary = f"{city}天气查询已完成"
        if weather:
            summary += f"，天气：{weather}"
        if low or high:
            summary += f"，温度：{low or '?'} ~ {high or '?'}"
        return summary

    if employee.get("alias") == "音乐":
        title = _find_text_in_tree(result, ["title", "name", "song", "music_name"])
        artist = _find_text_in_tree(result, ["author", "singer", "artist"])
        if title and artist:
            return f"已为你随机推荐：{title} - {artist}"
        if title:
            return f"已为你随机推荐：{title}"
        return "已获取一条随机音乐推荐"

    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False)[:280]
    return str(result)[:280]


def _extract_card_payload(employee, result):
    if employee.get("alias") != "音乐" or not isinstance(result, dict):
        return None
    return {
        "title": _find_text_in_tree(result, ["title", "name", "song", "music_name"]),
        "artist": _find_text_in_tree(result, ["author", "singer", "artist"]),
        "cover": _find_text_in_tree(result, ["pic", "cover", "image", "img"]),
        "url": _find_text_in_tree(result, ["url", "music_url", "play_url", "mp3"]),
        "lyric": _find_text_in_tree(result, ["lrc", "lyric"])
    }


def _parse_json_object(text):
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _first_non_empty(data, keys):
    if not isinstance(data, dict):
        return None
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def _find_text_in_tree(node, keys):
    if isinstance(node, dict):
        for key in keys:
            value = node.get(key)
            if isinstance(value, (str, int, float)) and value != "":
                return str(value)
        for value in node.values():
            found = _find_text_in_tree(value, keys)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_text_in_tree(item, keys)
            if found:
                return found
    return None


def _estimate_tokens(text):
    text = text or ""
    return max(1, int(len(text) / 3.5)) if text else 0


def _extract_content(data):
    choices = data.get("choices") or []
    if not choices:
        return ""
    first = choices[0]
    message = first.get("message") or {}
    if message.get("content") is not None:
        return message.get("content") or ""
    return first.get("text") or ""


def _extract_usage(data, prompt, completion):
    usage = data.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens") or _estimate_tokens(prompt))
    completion_tokens = int(usage.get("completion_tokens") or _estimate_tokens(completion))
    total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
    return prompt_tokens, completion_tokens, total_tokens


async def _call_openai_service(service, message, stream=False, streaming_callback=None):
    payload = {
        "model": service["model_name"],
        "messages": [{"role": "user", "content": message}],
        "temperature": float(service.get("temperature") or 0.7),
        "max_tokens": int(service.get("max_tokens") or 1024),
        "stream": bool(stream)
    }
    request = tornado.httpclient.HTTPRequest(
        url=service["endpoint_url"],
        method="POST",
        headers={
            "Authorization": "Bearer " + service["api_key"],
            "Content-Type": "application/json"
        },
        body=tornado.escape.json_encode(payload),
        request_timeout=120 if stream else 60,
        streaming_callback=streaming_callback,
        validate_cert=True
    )
    client = tornado.httpclient.AsyncHTTPClient()
    response = await client.fetch(request, raise_error=False)
    if response.code < 200 or response.code >= 300:
        body = (response.body or b"").decode("utf-8", errors="ignore")
        raise RuntimeError(f"模型调用失败：HTTP {response.code} {body[:300]}")
    if stream:
        return {}
    body = (response.body or b"{}").decode("utf-8", errors="ignore")
    return json.loads(body)


def _extract_stream_delta(data):
    choices = data.get("choices") or []
    if not choices:
        return ""
    delta = choices[0].get("delta") or {}
    if delta.get("content") is not None:
        return delta.get("content") or ""
    message = choices[0].get("message") or {}
    return message.get("content") or choices[0].get("text") or ""
