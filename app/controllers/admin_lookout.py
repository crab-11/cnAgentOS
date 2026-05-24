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
        source_id = int(self.get_body_argument("id", 0) or 0)
        source = LookoutSourceRepository.get_source_by_id(source_id)
        if not source:
            return self.write({"code": 1, "msg": "瞭望源不存在"})
        if source.get("status") != 1:
            return self.write({"code": 1, "msg": "瞭望源已禁用，不能执行采集"})

        task_id = LookoutTaskRepository.create_task(source_id=source_id, source_name=source["name"])
        try:
            items = await LookoutCollector.collect_source(source)
            fetched_count = len(items)
            stored_count = LookoutRecordRepository.add_records(source_id, items)
            LookoutTaskRepository.finish_task(
                task_id,
                status="success",
                fetched_count=fetched_count,
                stored_count=stored_count
            )
            LookoutSourceRepository.update_last_collected_at(source_id)
            self.write({
                "code": 0,
                "msg": "采集完成",
                "data": {
                    "task_id": task_id,
                    "fetched_count": fetched_count,
                    "stored_count": stored_count
                }
            })
        except Exception as e:
            LookoutTaskRepository.finish_task(task_id, status="failed", error_message=str(e)[:500])
            self.write({"code": 1, "msg": f"采集失败：{str(e)}"})


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


def _read_source_form(handler):
    return {
        "name": (handler.get_body_argument("name", "") or "").strip(),
        "source_type": (handler.get_body_argument("source_type", "website") or "website").strip(),
        "target_url": (handler.get_body_argument("target_url", "") or "").strip(),
        "parser_type": (handler.get_body_argument("parser_type", "html") or "html").strip(),
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
    if data["parser_type"] not in ("html", "rss", "json"):
        return "解析方式仅支持 html/rss/json"
    return None
