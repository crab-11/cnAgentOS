import tornado.web

from app.controllers.base import BaseHandler
from app.models.robot import DigitalEmployeeRepository, DigitalEmployeeService


class RobotOptionsHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.write({"code": 0, "msg": "成功", "data": DigitalEmployeeRepository.get_enabled_options()})


class RobotInvokeHandler(BaseHandler):
    @tornado.web.authenticated
    async def post(self):
        message = (self.get_body_argument("message", "") or "").strip()
        alias = (self.get_body_argument("alias", "") or "").strip()
        query = (self.get_body_argument("query", "") or "").strip()

        try:
            if message:
                result = await DigitalEmployeeService.invoke_from_message(message)
            else:
                if not alias:
                    raise ValueError("请输入 @别名 指令或单独提供 alias")
                employee = DigitalEmployeeRepository.get_employee_by_alias(alias)
                if not employee:
                    raise ValueError(f"未找到名为 @{alias} 的数字员工")
                result = await DigitalEmployeeService.invoke_employee(employee, query)
        except Exception as e:
            return self.write({"code": 1, "msg": str(e)})

        self.write({"code": 0, "msg": "成功", "data": result})


class RobotInvokeStreamHandler(BaseHandler):
    @tornado.web.authenticated
    async def get(self):
        message = (self.get_argument("message", "") or "").strip()
        alias = (self.get_argument("alias", "") or "").strip()
        query = (self.get_argument("query", "") or "").strip()

        self.set_header("Content-Type", "text/event-stream; charset=utf-8")
        self.set_header("Cache-Control", "no-cache")
        self.set_header("X-Accel-Buffering", "no")

        try:
            if message:
                parsed = DigitalEmployeeService.parse_message(message)
                if not parsed:
                    raise ValueError("请使用 @别名 指令，例如：@川小码 你好")
                alias = parsed["alias"]
                query = parsed["query"]

            if not alias:
                raise ValueError("缺少数字员工别名")

            employee = DigitalEmployeeRepository.get_employee_by_alias(alias)
            if not employee:
                raise ValueError(f"未找到名为 @{alias} 的数字员工")

            await DigitalEmployeeService.stream_employee(employee, query, self)
        except Exception as e:
            self.write("event: error\n")
            self.write("data: " + str(e).replace("\n", " ") + "\n\n")
            await self.flush()
