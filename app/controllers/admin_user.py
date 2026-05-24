# 后台用户管理控制器

import json
import tornado.web
from app.controllers.admin_auth import AdminBaseHandler
from app.models.user import UserRepository


class AdminUserHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_user.html", title="用户管理", username=self.current_user)


class AdminUserListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        username = (self.get_argument("username", "") or "").strip()

        result = UserRepository.get_user_list(
            page=page,
            page_size=limit,
            username=username if username else None
        )

        for item in result["list"]:
            if item.get("role") == "admin":
                item["role_name"] = "管理员"
            else:
                item["role_name"] = "普通用户"

        self.write({
            "code": 0,
            "msg": "成功",
            "data": {
                "list": result["list"],
                "total": result["total"]
            }
        })


class AdminUserAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        username = (self.get_body_argument("username", "") or "").strip()
        password = (self.get_body_argument("password", "") or "").strip()
        status = int(self.get_body_argument("status", 1))

        if not username or not password:
            return self.write({"code": 1, "msg": "用户名和密码不能为空"})

        if len(username) < 3 or len(username) > 30:
            return self.write({"code": 1, "msg": "用户名长度应在3-30个字符之间"})

        if len(password) < 6:
            return self.write({"code": 1, "msg": "密码长度不能少于6个字符"})

        success = UserRepository.create_user(username, password, status=status)

        if success:
            return self.write({"code": 0, "msg": "用户创建成功"})
        else:
            return self.write({"code": 1, "msg": "用户名已存在"})


class AdminUserUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        user_id = int(self.get_body_argument("id", 0))
        username = (self.get_body_argument("username", "") or "").strip()
        password = (self.get_body_argument("password", "") or "").strip()
        status = int(self.get_body_argument("status", 1))

        if not user_id:
            return self.write({"code": 1, "msg": "用户ID无效"})

        if not username:
            return self.write({"code": 1, "msg": "用户名不能为空"})

        current_user = UserRepository.get_user_by_id(user_id)
        if not current_user:
            return self.write({"code": 1, "msg": "用户不存在"})

        if password and len(password) < 6:
            return self.write({"code": 1, "msg": "密码长度不能少于6个字符"})

        update_password = password if password else None

        try:
            success = UserRepository.update_user(
                user_id=user_id,
                username=username,
                password=update_password,
                status=status
            )

            if success:
                return self.write({"code": 0, "msg": "用户更新成功"})
            else:
                return self.write({"code": 1, "msg": "更新失败，用户可能不存在"})
        except Exception as e:
            if "UNIQUE" in str(e):
                return self.write({"code": 1, "msg": "用户名已存在"})
            return self.write({"code": 1, "msg": "更新失败"})


class AdminUserDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        user_id = int(self.get_body_argument("id", 0))

        if not user_id:
            return self.write({"code": 1, "msg": "用户ID无效"})

        current_user = self.get_current_user()
        user_to_delete = UserRepository.get_user_by_username(current_user)

        if user_to_delete and user_to_delete["id"] == user_id:
            return self.write({"code": 1, "msg": "不能删除当前登录的账户"})

        success = UserRepository.delete_user(user_id)

        if success:
            return self.write({"code": 0, "msg": "用户删除成功"})
        else:
            return self.write({"code": 1, "msg": "删除失败，用户可能不存在"})


class AdminUserBatchDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        ids_str = (self.get_body_argument("ids", "") or "").strip()

        if not ids_str:
            return self.write({"code": 1, "msg": "请选择要删除的用户"})

        try:
            user_ids = json.loads(ids_str)
        except json.JSONDecodeError:
            return self.write({"code": 1, "msg": "参数格式错误"})

        if not user_ids or not isinstance(user_ids, list):
            return self.write({"code": 1, "msg": "请选择要删除的用户"})

        current_user = self.get_current_user()
        user_info = UserRepository.get_user_by_username(current_user)
        
        if user_info and user_info["id"] in user_ids:
            return self.write({"code": 1, "msg": "不能删除当前登录的账户，请从批量选择中移除"})

        deleted_count = UserRepository.batch_delete_user(user_ids)

        if deleted_count > 0:
            return self.write({"code": 0, "msg": f"成功删除 {deleted_count} 个用户"})
        else:
            return self.write({"code": 1, "msg": "删除失败"})


class AdminStatsHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        user_count = UserRepository.get_user_count()

        self.write({
            "code": 0,
            "msg": "成功",
            "data": {
                "user_count": user_count
            }
        })
