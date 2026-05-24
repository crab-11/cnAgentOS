import json

import tornado.web

from app.controllers.admin_auth import AdminBaseHandler
from app.models.lookout import (
    LookoutCollector,
    LookoutRecordRepository,
    LookoutSourceRepository,
    LookoutTaskRepository
)


class AdminLookoutSourceHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_lookout_source.html", title="瞭望源管理", username=self.current_user)


class AdminLookoutWorkbenchHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_lookout_collect.html", title="瞭望采集", username=self.current_user)


class AdminLookoutSourceListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1) or 1)
        limit = int(self.get_argument("limit", 20) or 20)
        keyword = (self.get_argument("keyword", "") or "").strip()
        status_arg = (self.get_argument("status", "") or "").strip()
        status = int(status_arg) if status_arg in ("0", "1") else None
        data = LookoutSourceRepository.get_source_list(
            page=page,
            page_size=limit,
            keyword=keyword if keyword else None,
            status=status
        )
        self.write({"code": 0, "msg": "成功", "data": data})


class AdminLookoutSourceOptionsHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        sources = LookoutSourceRepository.get_enabled_sources()
        self.write({"code": 0, "msg": "成功", "data": sources})


class AdminLookoutSourceAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        data = _read_source_form(self)
        error = _validate_source_form(data)
        if error:
            return self.write({"code": 1, "msg": error})

        source_id = LookoutSourceRepository.create_source(**data)
        if source_id:
            return self.write({"code": 0, "msg": "瞭望源创建成功", "data": {"id": source_id}})
        self.write({"code": 1, "msg": "瞭望源创建失败，名称可能已存在"})


class AdminLookoutSourceUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        source_id = int(self.get_body_argument("id", 0) or 0)
        if not source_id:
            return self.write({"code": 1, "msg": "瞭望源ID无效"})

        data = _read_source_form(self)
        error = _validate_source_form(data)
        if error:
            return self.write({"code": 1, "msg": error})

        success = LookoutSourceRepository.update_source(source_id=source_id, **data)
        if success:
            return self.write({"code": 0, "msg": "瞭望源更新成功"})
        self.write({"code": 1, "msg": "瞭望源不存在、名称重复或更新失败"})


class AdminLookoutSourceDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        source_id = int(self.get_body_argument("id", 0) or 0)
        if not source_id:
            return self.write({"code": 1, "msg": "瞭望源ID无效"})
        success = LookoutSourceRepository.delete_source(source_id)
        if success:
            return self.write({"code": 0, "msg": "瞭望源删除成功"})
        self.write({"code": 1, "msg": "瞭望源不存在或删除失败"})


class AdminLookoutCollectHandler(AdminBaseHandler):
    @tornado.web.authenticated
    async def post(self):
        source_ids = _parse_source_ids(self.get_body_argument("source_ids", ""))
        keyword = (self.get_body_argument("keyword", "") or "").strip()
        page_count = int(self.get_body_argument("page_count", 1) or 1)
        page_size = int(self.get_body_argument("page_size", 20) or 20)

        if not source_ids:
            single_id = int(self.get_body_argument("id", 0) or 0)
            if single_id:
                source_ids = [single_id]
        if not source_ids:
            return self.write({"code": 1, "msg": "请选择至少一个采集源"})
        if page_count <= 0 or page_count > 20:
            return self.write({"code": 1, "msg": "采集页数必须在 1 到 20 之间"})
        if page_size <= 0 or page_size > 200:
            return self.write({"code": 1, "msg": "一次有效采集数量必须在 1 到 200 之间"})

        summaries = []
        previews = []
        total_fetched = 0
        total_stored = 0

        for source_id in source_ids:
            source = LookoutSourceRepository.get_source_by_id(source_id)
            if not source:
                summaries.append({"source_id": source_id, "status": "failed", "message": "瞭望源不存在"})
                continue
            if source.get("status") != 1:
                summaries.append({"source_id": source_id, "source_name": source["name"], "status": "failed", "message": "瞭望源已禁用"})
                continue

            task_id = LookoutTaskRepository.create_task(
                source_id=source_id,
                source_name=source["name"],
                keyword=keyword or None,
                page_count=page_count,
                page_size=page_size
            )
            try:
                items = await LookoutCollector.collect_source(
                    source,
                    keyword=keyword or None,
                    page_count=page_count,
                    page_size=page_size
                )
                fetched_count = len(items)
                stored_count = LookoutRecordRepository.add_records(source_id, keyword or None, items)
                LookoutTaskRepository.finish_task(
                    task_id,
                    status="success",
                    fetched_count=fetched_count,
                    stored_count=stored_count
                )
                LookoutSourceRepository.update_last_collected_at(source_id)
                total_fetched += fetched_count
                total_stored += stored_count
                summaries.append({
                    "source_id": source_id,
                    "source_name": source["name"],
                    "status": "success",
                    "task_id": task_id,
                    "fetched_count": fetched_count,
                    "stored_count": stored_count
                })
                for item in items[:5]:
                    previews.append({
                        "source_name": source["name"],
                        "title": item.get("title"),
                        "summary": item.get("summary"),
                        "content_url": item.get("content_url"),
                        "published_at": item.get("published_at")
                    })
            except Exception as e:
                LookoutTaskRepository.finish_task(task_id, status="failed", error_message=str(e)[:500])
                summaries.append({
                    "source_id": source_id,
                    "source_name": source["name"],
                    "status": "failed",
                    "task_id": task_id,
                    "message": str(e)
                })

        if not any(item["status"] == "success" for item in summaries):
            return self.write({"code": 1, "msg": "采集失败", "data": {"sources": summaries}})

        self.write({
            "code": 0,
            "msg": "采集完成",
            "data": {
                "keyword": keyword,
                "page_count": page_count,
                "page_size": page_size,
                "total_fetched": total_fetched,
                "total_stored": total_stored,
                "sources": summaries,
                "preview": previews[:12]
            }
        })


class AdminLookoutTaskListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1) or 1)
        limit = int(self.get_argument("limit", 20) or 20)
        source_id = int(self.get_argument("source_id", 0) or 0)
        data = LookoutTaskRepository.get_task_list(
            page=page,
            page_size=limit,
            source_id=source_id or None
        )
        self.write({"code": 0, "msg": "成功", "data": data})


class AdminDataWarehouseHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_data_warehouse.html", title="数据仓库", username=self.current_user)


class AdminDataWarehouseListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1) or 1)
        limit = int(self.get_argument("limit", 20) or 20)
        keyword = (self.get_argument("keyword", "") or "").strip()
        source_id = int(self.get_argument("source_id", 0) or 0)
        data = LookoutRecordRepository.get_record_list(
            page=page,
            page_size=limit,
            keyword=keyword if keyword else None,
            source_id=source_id or None
        )
        self.write({"code": 0, "msg": "成功", "data": data})


class AdminDataWarehouseDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        record_id = int(self.get_body_argument("id", 0) or 0)
        if not record_id:
            return self.write({"code": 1, "msg": "记录ID无效"})
        success = LookoutRecordRepository.delete_record(record_id)
        if success:
            return self.write({"code": 0, "msg": "记录删除成功"})
        self.write({"code": 1, "msg": "记录不存在或删除失败"})


class AdminDataWarehouseBatchDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        ids_raw = self.get_body_argument("ids", "") or ""
        record_ids = [int(item) for item in ids_raw.split(",") if item.strip().isdigit()]
        if not record_ids:
            return self.write({"code": 1, "msg": "请至少选择一条记录"})
        deleted_count = LookoutRecordRepository.batch_delete(record_ids)
        self.write({"code": 0, "msg": f"已删除 {deleted_count} 条记录"})


def _read_source_form(handler):
    return {
        "name": (handler.get_body_argument("name", "") or "").strip(),
        "source_type": (handler.get_body_argument("source_type", "website") or "website").strip(),
        "target_url": (handler.get_body_argument("target_url", "") or "").strip(),
        "request_method": (handler.get_body_argument("request_method", "GET") or "GET").strip().upper(),
        "parser_type": (handler.get_body_argument("parser_type", "html") or "html").strip(),
        "request_headers": (handler.get_body_argument("request_headers", "") or "").strip() or None,
        "default_params": (handler.get_body_argument("default_params", "") or "").strip() or None,
        "param_config": (handler.get_body_argument("param_config", "") or "").strip() or None,
        "extract_rules": (handler.get_body_argument("extract_rules", "") or "").strip() or None,
        "page_param": (handler.get_body_argument("page_param", "pn") or "pn").strip(),
        "page_step": int(handler.get_body_argument("page_step", 10) or 10),
        "keyword_param": (handler.get_body_argument("keyword_param", "word") or "word").strip(),
        "keywords": (handler.get_body_argument("keywords", "") or "").strip() or None,
        "status": int(handler.get_body_argument("status", 1) or 1),
        "remark": (handler.get_body_argument("remark", "") or "").strip() or None
    }


def _validate_source_form(data):
    if not data["name"]:
        return "瞭望源名称不能为空"
    if not data["target_url"]:
        return "采集地址不能为空"
    if not data["target_url"].startswith(("http://", "https://")):
        return "采集地址必须以 http:// 或 https:// 开头"
    if data["request_method"] not in ("GET", "POST"):
        return "请求方法仅支持 GET/POST"
    if data["parser_type"] not in ("html", "rss", "json", "baidu_news"):
        return "解析方式仅支持 html/rss/json/baidu_news"
    if data["page_step"] <= 0:
        return "分页步进必须大于 0"
    for field_name in ("request_headers", "default_params", "extract_rules"):
        if data[field_name]:
            try:
                parsed = json.loads(data[field_name])
            except json.JSONDecodeError:
                return f"{field_name} 不是合法 JSON"
            if not isinstance(parsed, dict):
                return f"{field_name} 必须是 JSON 对象"
    if data["param_config"]:
        try:
            parsed = json.loads(data["param_config"])
        except json.JSONDecodeError:
            return "param_config 不是合法 JSON"
        if not isinstance(parsed, list):
            return "param_config 必须是 JSON 数组"
    return None


def _parse_source_ids(raw):
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [int(item) for item in parsed if str(item).isdigit()]
    except json.JSONDecodeError:
        pass
    return [int(item) for item in raw.split(",") if item.strip().isdigit()]
