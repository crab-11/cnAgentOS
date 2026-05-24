import tornado.web
from app.controllers.admin_auth import AdminBaseHandler
from app.models.permission import PermissionRepository


class AdminPermissionHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_permission.html", title="功能管理", username=self.current_user)


class AdminPermissionListHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        name = (self.get_argument("name", "") or "").strip()
        category = (self.get_argument("category", "") or "").strip()

        rows = PermissionRepository.get_permission_flat_tree(
            name=name if name else None,
            category=category if category else None
        )

        for item in rows:
            if item.get("status") == 1:
                item["status_name"] = "正常"
            else:
                item["status_name"] = "禁用"
            if item.get("category") == "group":
                item["category_name"] = "分组"
            else:
                item["category_name"] = "菜单"

        self.write({
            "code": 0,
            "msg": "成功",
            "data": {
                "list": rows,
                "total": len(rows)
            }
        })


class AdminPermissionTreeHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        tree = PermissionRepository.get_permission_tree()
        self.write({
            "code": 0,
            "msg": "成功",
            "data": tree
        })


class AdminPermissionAddHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        name = (self.get_body_argument("name", "") or "").strip()
        display_name = (self.get_body_argument("display_name", "") or "").strip()
        code = (self.get_body_argument("code", "") or "").strip()
        category = (self.get_body_argument("category", "menu") or "menu").strip()
        parent_id = int(self.get_body_argument("parent_id", 0) or 0)
        icon = (self.get_body_argument("icon", "") or "").strip() or None
        url = (self.get_body_argument("url", "") or "").strip() or None
        sort_order = int(self.get_body_argument("sort_order", 0) or 0)

        display_name = display_name or name
        if not name or not code:
            return self.write({"code": 1, "msg": "功能名称和功能标识不能为空"})

        success = PermissionRepository.create_permission(
            name=name,
            display_name=display_name,
            code=code,
            category=category,
            parent_id=parent_id,
            icon=icon,
            url=url,
            sort_order=sort_order
        )

        if success:
            return self.write({"code": 0, "msg": "功能创建成功"})
        else:
            return self.write({"code": 1, "msg": "功能创建失败，代码可能已存在"})


class AdminPermissionUpdateHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        permission_id = int(self.get_body_argument("id", 0))

        if not permission_id:
            return self.write({"code": 1, "msg": "功能ID无效"})

        permission = PermissionRepository.get_permission_by_id(permission_id)
        if not permission:
            return self.write({"code": 1, "msg": "功能不存在"})

        name = (self.get_body_argument("name", "") or "").strip()
        display_name = (self.get_body_argument("display_name", "") or "").strip()
        code = (self.get_body_argument("code", "") or "").strip()
        category = (self.get_body_argument("category", "") or "").strip()
        parent_id = self.get_body_argument("parent_id", None)
        icon = (self.get_body_argument("icon", "") or "").strip() or None
        url = (self.get_body_argument("url", "") or "").strip() or None
        sort_order = self.get_body_argument("sort_order", None)
        status = self.get_body_argument("status", None)

        if parent_id is not None:
            parent_id = int(parent_id) if parent_id else 0
        if sort_order is not None:
            sort_order = int(sort_order) if sort_order else 0
        if status is not None:
            status = int(status) if status else 0

        display_name = display_name or name
        if not name or not code:
            return self.write({"code": 1, "msg": "功能名称和功能标识不能为空"})

        success = PermissionRepository.update_permission(
            permission_id=permission_id,
            name=name,
            display_name=display_name,
            code=code,
            category=category if category else None,
            parent_id=parent_id,
            icon=icon,
            url=url,
            sort_order=sort_order,
            status=status
        )

        if success:
            return self.write({"code": 0, "msg": "功能更新成功"})
        else:
            return self.write({"code": 1, "msg": "功能更新失败"})


class AdminPermissionDeleteHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def post(self):
        permission_id = int(self.get_body_argument("id", 0))

        if not permission_id:
            return self.write({"code": 1, "msg": "功能ID无效"})

        permission = PermissionRepository.get_permission_by_id(permission_id)
        if not permission:
            return self.write({"code": 1, "msg": "功能不存在"})

        success = PermissionRepository.delete_permission(permission_id)

        if success:
            return self.write({"code": 0, "msg": "功能删除成功"})
        else:
            return self.write({"code": 1, "msg": "功能删除失败"})


class AdminPermissionMenusHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        parent_id = int(self.get_argument("parent_id", 0) or 0)
        menus = PermissionRepository.get_menus_by_parent(parent_id)
        self.write({
            "code": 0,
            "msg": "成功",
            "data": menus
        })
