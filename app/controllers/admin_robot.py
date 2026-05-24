import sqlite3

import tornado.web

from app.controllers.admin_auth import AdminBaseHandler
from app.models.api_interface import ApiInterfaceRepository
from app.models.model_service import ModelServiceRepository
from app.models.robot import DigitalEmployeeRepository, DigitalEmployeeService


class AdminRobotHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_robot.html", title="数字员工", username=self.current_user)


class AdminRobotListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1) or 1)
        limit = int(self.get_argument("limit", 20) or 20)
        keyword = (self.get_argument("keyword", "") or "").strip()
        status_arg = (self.get_argument("status", "") or "").strip()
        employee_type = (self.get_argument("employee_type", "") or "").strip()
        status = int(status_arg) if status_arg in ("0", "1") else None

        result = DigitalEmployeeRepository.get_employee_list(
            page=page,
            page_size=limit,
            keyword=keyword if keyword else None,
            status=status,
            employee_type=employee_type if employee_type else None
        )
        self.write({"code": 0, "msg": "成功", "data": result})


class AdminRobotDetailHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        employee_id = int(self.get_argument("id", 0) or 0)
        if not employee_id:
            return self.write({"code": 1, "msg": "数字员工ID无效"})
        item = DigitalEmployeeRepository.get_employee_by_id(employee_id)
        if not item:
            return self.write({"code": 1, "msg": "数字员工不存在"})
        self.write({"code": 0, "msg": "成功", "data": item})


class AdminRobotOptionsHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.write({
            "code": 0,
            "msg": "成功",
            "data": {
                "models": ModelServiceRepository.get_service_list(page=1, page_size=200, status=1)["list"],
                "apis": ApiInterfaceRepository.get_enabled_interfaces()
            }
        })


class AdminRobotAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        data = _read_employee_form(self)
        error = _validate_employee_form(data)
        if error:
            return self.write({"code": 1, "msg": error})
        try:
            employee_id = DigitalEmployeeRepository.create_employee(**data)
        except sqlite3.IntegrityError:
            return self.write({"code": 1, "msg": "别名已存在，请更换"})
        self.write({"code": 0, "msg": "数字员工创建成功", "data": {"id": employee_id}})


class AdminRobotUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        employee_id = int(self.get_body_argument("id", 0) or 0)
        if not employee_id:
            return self.write({"code": 1, "msg": "数字员工ID无效"})
        data = _read_employee_form(self)
        error = _validate_employee_form(data)
        if error:
            return self.write({"code": 1, "msg": error})
        try:
            success = DigitalEmployeeRepository.update_employee(employee_id=employee_id, **data)
        except sqlite3.IntegrityError:
            return self.write({"code": 1, "msg": "别名已存在，请更换"})
        if not success:
            return self.write({"code": 1, "msg": "数字员工不存在或更新失败"})
        self.write({"code": 0, "msg": "数字员工更新成功"})


class AdminRobotDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        employee_id = int(self.get_body_argument("id", 0) or 0)
        if not employee_id:
            return self.write({"code": 1, "msg": "数字员工ID无效"})
        success = DigitalEmployeeRepository.delete_employee(employee_id)
        if not success:
            return self.write({"code": 1, "msg": "数字员工不存在或删除失败"})
        self.write({"code": 0, "msg": "数字员工删除成功"})


class AdminRobotTestHandler(AdminBaseHandler):
    @tornado.web.authenticated
    async def post(self):
        employee_id = int(self.get_body_argument("id", 0) or 0)
        query = (self.get_body_argument("query", "") or "").strip()
        employee = DigitalEmployeeRepository.get_employee_by_id(employee_id)
        if not employee or int(employee.get("status") or 0) != 1:
            return self.write({"code": 1, "msg": "数字员工不存在或已禁用"})
        try:
            result = await DigitalEmployeeService.invoke_employee(employee, query)
        except Exception as e:
            return self.write({"code": 1, "msg": str(e)})
        self.write({"code": 0, "msg": "调用成功", "data": result})


class AdminRobotTestStreamHandler(AdminBaseHandler):
    @tornado.web.authenticated
    async def get(self):
        employee_id = int(self.get_argument("id", 0) or 0)
        query = (self.get_argument("query", "") or "").strip()
        employee = DigitalEmployeeRepository.get_employee_by_id(employee_id)

        self.set_header("Content-Type", "text/event-stream; charset=utf-8")
        self.set_header("Cache-Control", "no-cache")
        self.set_header("X-Accel-Buffering", "no")

        if not employee or int(employee.get("status") or 0) != 1:
            self.write("event: error\n")
            self.write("data: 数字员工不存在或已禁用\n\n")
            await self.flush()
            return
        try:
            await DigitalEmployeeService.stream_employee(employee, query, self)
        except Exception as e:
            self.write("event: error\n")
            self.write("data: " + str(e).replace("\n", " ") + "\n\n")
            await self.flush()


def _read_employee_form(handler):
    return {
        "name": (handler.get_body_argument("name", "") or "").strip(),
        "alias": (handler.get_body_argument("alias", "") or "").strip(),
        "employee_type": (handler.get_body_argument("employee_type", "normal") or "normal").strip(),
        "service_type": (handler.get_body_argument("service_type", "api") or "api").strip(),
        "description": (handler.get_body_argument("description", "") or "").strip() or None,
        "prompt_template": (handler.get_body_argument("prompt_template", "") or "").strip() or None,
        "model_service_id": int(handler.get_body_argument("model_service_id", 0) or 0) or None,
        "use_default_model": int(handler.get_body_argument("use_default_model", 0) or 0),
        "api_interface_id": int(handler.get_body_argument("api_interface_id", 0) or 0) or None,
        "request_param_name": (handler.get_body_argument("request_param_name", "") or "").strip() or None,
        "request_param_template": (handler.get_body_argument("request_param_template", "") or "").strip() or None,
        "response_mode": (handler.get_body_argument("response_mode", "text") or "text").strip(),
        "status": int(handler.get_body_argument("status", 0) or 0),
        "remark": (handler.get_body_argument("remark", "") or "").strip() or None
    }


def _validate_employee_form(data):
    if not data["name"]:
        return "员工名称不能为空"
    if not data["alias"]:
        return "员工别名不能为空"
    if not data["alias"].isalnum() and not all("\u4e00" <= ch <= "\u9fff" or ch.isalnum() for ch in data["alias"]):
        return "员工别名仅支持中文、英文和数字"
    if data["employee_type"] not in ("ai", "normal"):
        return "员工分类仅支持 ai / normal"
    if data["service_type"] not in ("model", "api"):
        return "服务类型仅支持 model / api"
    if data["response_mode"] not in ("text", "json", "card", "sse"):
        return "响应模式不合法"
    if data["service_type"] == "model":
        if int(data["use_default_model"] or 0) != 1 and not data["model_service_id"]:
            return "模型员工请绑定专属模型或启用默认模型"
    if data["service_type"] == "api" and not data["api_interface_id"]:
        return "API 员工必须绑定接口服务"
    return None
