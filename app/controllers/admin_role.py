import tornado.web
from app.controllers.admin_auth import AdminBaseHandler
from app.models.role import RoleRepository
from app.models.permission import PermissionRepository


class AdminRoleHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_role.html", title="角色管理", username=self.current_user)


class AdminRoleListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        name = (self.get_argument("name", "") or "").strip()

        result = RoleRepository.get_role_list(
            page=page,
            page_size=limit,
            name=name if name else None
        )

        for item in result["list"]:
            if item.get("is_system") == 1:
                item["is_system_name"] = "是"
                item["can_edit"] = False
                item["can_delete"] = False
            else:
                item["is_system_name"] = "否"
                item["can_edit"] = True
                item["can_delete"] = True

            if item.get("status") == 1:
                item["status_name"] = "正常"
            else:
                item["status_name"] = "禁用"

            permissions = RoleRepository.get_role_permissions(item["id"])
            item["permission_count"] = len(permissions)

        self.write({
            "code": 0,
            "msg": "成功",
            "data": {
                "list": result["list"],
                "total": result["total"]
            }
        })


class AdminRoleAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        name = (self.get_body_argument("name", "") or "").strip()
        display_name = (self.get_body_argument("display_name", "") or "").strip()
        description = (self.get_body_argument("description", "") or "").strip() or None

        if not name or not display_name:
            return self.write({"code": 1, "msg": "角色名称和显示名称不能为空"})

        if len(name) < 2 or len(name) > 20:
            return self.write({"code": 1, "msg": "角色名称长度应在2-20个字符之间"})

        success = RoleRepository.create_role(
            name=name,
            display_name=display_name,
            description=description
        )

        if success:
            return self.write({"code": 0, "msg": "角色创建成功"})
        else:
            return self.write({"code": 1, "msg": "角色创建失败，角色代码可能已存在"})


class AdminRoleUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        role_id = int(self.get_body_argument("id", 0))

        if not role_id:
            return self.write({"code": 1, "msg": "角色ID无效"})

        role = RoleRepository.get_role_by_id(role_id)
        if not role:
            return self.write({"code": 1, "msg": "角色不存在"})

        if role.get("is_system") == 1:
            return self.write({"code": 1, "msg": "系统内置角色不能修改"})

        display_name = (self.get_body_argument("display_name", "") or "").strip()
        description = (self.get_body_argument("description", "") or "").strip() or None
        status = self.get_body_argument("status", None)

        if not display_name:
            return self.write({"code": 1, "msg": "显示名称不能为空"})

        if status is not None:
            status = int(status)

        success = RoleRepository.update_role(
            role_id=role_id,
            display_name=display_name,
            description=description,
            status=status
        )

        if success:
            return self.write({"code": 0, "msg": "角色更新成功"})
        else:
            return self.write({"code": 1, "msg": "角色更新失败"})


class AdminRoleDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        role_id = int(self.get_body_argument("id", 0))

        if not role_id:
            return self.write({"code": 1, "msg": "角色ID无效"})

        role = RoleRepository.get_role_by_id(role_id)
        if not role:
            return self.write({"code": 1, "msg": "角色不存在"})

        if role.get("is_system") == 1:
            return self.write({"code": 1, "msg": "系统内置角色不能删除"})

        success = RoleRepository.delete_role(role_id)

        if success:
            return self.write({"code": 0, "msg": "角色删除成功"})
        else:
            return self.write({"code": 1, "msg": "角色删除失败"})


class AdminRolePermissionsHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        role_id = int(self.get_argument("role_id", 0))

        if not role_id:
            return self.write({"code": 1, "msg": "角色ID无效"})

        role = RoleRepository.get_role_by_id(role_id)
        if not role:
            return self.write({"code": 1, "msg": "角色不存在"})

        permissions = RoleRepository.get_role_permissions(role_id)
        permission_ids = [p["id"] for p in permissions]

        self.write({
            "code": 0,
            "msg": "成功",
            "data": {
                "permission_ids": permission_ids,
                "permissions": permissions
            }
        })

    @tornado.web.authenticated
    def post(self):
        role_id = int(self.get_body_argument("role_id", 0))
        permission_ids_str = (self.get_body_argument("permission_ids", "") or "").strip()

        if not role_id:
            return self.write({"code": 1, "msg": "角色ID无效"})

        role = RoleRepository.get_role_by_id(role_id)
        if not role:
            return self.write({"code": 1, "msg": "角色不存在"})

        if role.get("is_system") == 1:
            return self.write({"code": 1, "msg": "系统内置角色不能修改权限"})

        permission_ids = []
        if permission_ids_str:
            try:
                permission_ids = [int(x) for x in permission_ids_str.split(",") if x]
            except ValueError:
                return self.write({"code": 1, "msg": "权限参数格式错误"})

        success = RoleRepository.set_role_permissions(role_id, permission_ids)

        if success:
            return self.write({"code": 0, "msg": "权限分配成功"})
        else:
            return self.write({"code": 1, "msg": "权限分配失败"})


class AdminRoleAllPermissionsHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        tree = PermissionRepository.get_permission_tree()
        self.write({
            "code": 0,
            "msg": "成功",
            "data": tree
        })