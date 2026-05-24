import json
import time

import tornado.escape
import tornado.httpclient
import tornado.web

from app.controllers.admin_auth import AdminBaseHandler
from app.models.model_service import ModelServiceRepository


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


def _service_payload(service, message, stream=False):
    payload = {
        "model": service["model_name"],
        "messages": [
            {"role": "user", "content": message}
        ],
        "temperature": float(service.get("temperature") or 0.7),
        "max_tokens": int(service.get("max_tokens") or 1024),
        "stream": bool(stream)
    }
    return payload


class AdminModelHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_model.html", title="模型引擎", username=self.current_user)


class AdminModelListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1) or 1)
        limit = int(self.get_argument("limit", 6) or 6)
        keyword = (self.get_argument("keyword", "") or "").strip()
        status_arg = (self.get_argument("status", "") or "").strip()
        status = int(status_arg) if status_arg in ("0", "1") else None

        result = ModelServiceRepository.get_service_list(
            page=page,
            page_size=limit,
            keyword=keyword if keyword else None,
            status=status
        )
        self.write({"code": 0, "msg": "成功", "data": result})


class AdminModelDetailHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        service_id = int(self.get_argument("id", 0) or 0)
        service = ModelServiceRepository.get_service_by_id(service_id)
        if not service:
            return self.write({"code": 1, "msg": "模型服务不存在"})
        self.write({"code": 0, "msg": "成功", "data": service})


class AdminModelAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        data = self._read_form()
        error = self._validate(data, require_key=True)
        if error:
            return self.write({"code": 1, "msg": error})

        service_id = ModelServiceRepository.create_service(**data)
        if service_id:
            return self.write({"code": 0, "msg": "模型服务创建成功", "data": {"id": service_id}})
        return self.write({"code": 1, "msg": "模型服务创建失败"})

    def _read_form(self):
        return _read_service_form(self)

    def _validate(self, data, require_key=False):
        return _validate_service_form(data, require_key=require_key)


class AdminModelUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        service_id = int(self.get_body_argument("id", 0) or 0)
        if not service_id:
            return self.write({"code": 1, "msg": "模型服务ID无效"})

        data = _read_service_form(self)
        error = _validate_service_form(data, require_key=False)
        if error:
            return self.write({"code": 1, "msg": error})

        success = ModelServiceRepository.update_service(service_id=service_id, **data)
        if success:
            return self.write({"code": 0, "msg": "模型服务更新成功"})
        return self.write({"code": 1, "msg": "模型服务不存在或更新失败"})


class AdminModelDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        service_id = int(self.get_body_argument("id", 0) or 0)
        if not service_id:
            return self.write({"code": 1, "msg": "模型服务ID无效"})
        success = ModelServiceRepository.delete_service(service_id)
        if success:
            return self.write({"code": 0, "msg": "模型服务删除成功"})
        return self.write({"code": 1, "msg": "模型服务不存在或删除失败"})


class AdminModelDefaultHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        service_id = int(self.get_body_argument("id", 0) or 0)
        if not service_id:
            return self.write({"code": 1, "msg": "模型服务ID无效"})
        success = ModelServiceRepository.set_default(service_id)
        if success:
            return self.write({"code": 0, "msg": "默认模型已更新"})
        return self.write({"code": 1, "msg": "只能将启用中的模型设为默认"})


class AdminModelStatsHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        service_id = int(self.get_argument("service_id", 0) or 0)
        days = int(self.get_argument("days", 7) or 7)
        data = ModelServiceRepository.get_token_stats(service_id=service_id or None, days=days)
        self.write({"code": 0, "msg": "成功", "data": data})


class AdminModelTestHandler(AdminBaseHandler):
    @tornado.web.authenticated
    async def post(self):
        service_id = int(self.get_body_argument("service_id", 0) or 0)
        message = (self.get_body_argument("message", "") or "").strip()
        if not service_id:
            return self.write({"code": 1, "msg": "请选择模型服务"})
        if not message:
            return self.write({"code": 1, "msg": "请输入测试消息"})

        service = ModelServiceRepository.get_service_by_id(service_id, include_secret=True)
        if not service or service.get("status") != 1:
            return self.write({"code": 1, "msg": "模型服务不存在或已禁用"})

        start_time = time.time()
        try:
            response_data = await _call_openai_service(service, message, stream=False)
            content = _extract_content(response_data)
            latency_ms = int((time.time() - start_time) * 1000)
            prompt_tokens, completion_tokens, total_tokens = _extract_usage(response_data, message, content)
            ModelServiceRepository.record_call(
                service_id=service_id,
                model_name=service["model_name"],
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                success=1
            )
            return self.write({
                "code": 0,
                "msg": "调用成功",
                "data": {
                    "content": content,
                    "latency_ms": latency_ms,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
            })
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            ModelServiceRepository.record_call(
                service_id=service_id,
                model_name=service["model_name"],
                latency_ms=latency_ms,
                success=0,
                error_message=str(e)[:500]
            )
            return self.write({"code": 1, "msg": f"模型调用失败：{str(e)}"})


class AdminModelStreamTestHandler(AdminBaseHandler):
    @tornado.web.authenticated
    async def get(self):
        service_id = int(self.get_argument("service_id", 0) or 0)
        message = (self.get_argument("message", "") or "").strip()
        service = ModelServiceRepository.get_service_by_id(service_id, include_secret=True)

        self.set_header("Content-Type", "text/event-stream; charset=utf-8")
        self.set_header("Cache-Control", "no-cache")
        self.set_header("X-Accel-Buffering", "no")

        if not service or service.get("status") != 1:
            self.write("event: error\n")
            self.write("data: 模型服务不存在或已禁用\n\n")
            await self.flush()
            return
        if not message:
            self.write("event: error\n")
            self.write("data: 请输入测试消息\n\n")
            await self.flush()
            return

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
                    self.write("event: done\n")
                    self.write("data: [DONE]\n\n")
                    self.flush()
                    continue
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                delta = _extract_stream_delta(data)
                if delta:
                    output["text"] += delta
                    self.write("data: " + json.dumps({"delta": delta}, ensure_ascii=False) + "\n\n")
                    self.flush()

        try:
            await _call_openai_service(service, message, stream=True, streaming_callback=on_chunk)
            latency_ms = int((time.time() - start_time) * 1000)
            prompt_tokens = _estimate_tokens(message)
            completion_tokens = _estimate_tokens(output["text"])
            ModelServiceRepository.record_call(
                service_id=service_id,
                model_name=service["model_name"],
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                latency_ms=latency_ms,
                success=1
            )
            self.write("event: summary\n")
            self.write("data: " + json.dumps({
                "latency_ms": latency_ms,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }, ensure_ascii=False) + "\n\n")
            self.write("event: done\n")
            self.write("data: [DONE]\n\n")
            await self.flush()
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            ModelServiceRepository.record_call(
                service_id=service_id,
                model_name=service["model_name"],
                latency_ms=latency_ms,
                success=0,
                error_message=str(e)[:500]
            )
            self.write("event: error\n")
            self.write("data: " + str(e).replace("\n", " ") + "\n\n")
            await self.flush()


def _read_service_form(handler):
    return {
        "name": (handler.get_body_argument("name", "") or "").strip(),
        "provider": (handler.get_body_argument("provider", "") or "").strip(),
        "endpoint_url": (handler.get_body_argument("endpoint_url", "") or "").strip(),
        "api_key": (handler.get_body_argument("api_key", "") or "").strip(),
        "model_name": (handler.get_body_argument("model_name", "") or "").strip(),
        "temperature": float(handler.get_body_argument("temperature", 0.7) or 0.7),
        "max_tokens": int(handler.get_body_argument("max_tokens", 1024) or 1024),
        "stream_enabled": int(handler.get_body_argument("stream_enabled", 0) or 0),
        "is_default": int(handler.get_body_argument("is_default", 0) or 0),
        "status": int(handler.get_body_argument("status", 0) or 0),
        "remark": (handler.get_body_argument("remark", "") or "").strip() or None
    }


def _validate_service_form(data, require_key=False):
    if not data["name"]:
        return "服务名称不能为空"
    if not data["provider"]:
        return "服务商不能为空"
    if not data["endpoint_url"]:
        return "接口地址不能为空"
    if not data["endpoint_url"].startswith(("http://", "https://")):
        return "接口地址必须以 http:// 或 https:// 开头"
    if require_key and not data["api_key"]:
        return "API Key不能为空"
    if not data["model_name"]:
        return "模型名称不能为空"
    if data["temperature"] < 0 or data["temperature"] > 2:
        return "temperature 必须在 0 到 2 之间"
    if data["max_tokens"] <= 0:
        return "max_tokens 必须大于 0"
    return None


async def _call_openai_service(service, message, stream=False, streaming_callback=None):
    payload = _service_payload(service, message, stream=stream)
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
        raise RuntimeError(f"HTTP {response.code} {body[:300]}")
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
