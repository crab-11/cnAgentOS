# 程序的主入口
# 承担服务器容器 + 程序作用
# 服务器容器: 提供 http 容器服务，程序放置于该容器中运行
# 程序: 智能瞭望与智能问数系统

import os
import tornado.ioloop
import tornado.web
from tornado.httpserver import HTTPServer

# 引入 controller 层
from app.controllers.auth import LoginHandler, LogoutHandler
from app.controllers.home import IndexHandler

# 引入后台管理 controller 层
from app.controllers.admin_auth import AdminLoginHandler, AdminLogoutHandler
from app.controllers.admin_home import AdminIndexHandler
from app.controllers.admin_user import (
    AdminUserHandler,
    AdminUserListHandler,
    AdminUserAddHandler,
    AdminUserUpdateHandler,
    AdminUserDeleteHandler,
    AdminUserBatchDeleteHandler,
    AdminStatsHandler
)
from app.controllers.admin_permission import (
    AdminPermissionHandler,
    AdminPermissionListHandler,
    AdminPermissionTreeHandler,
    AdminPermissionAddHandler,
    AdminPermissionUpdateHandler,
    AdminPermissionDeleteHandler,
    AdminPermissionMenusHandler
)
from app.controllers.admin_role import (
    AdminRoleHandler,
    AdminRoleListHandler,
    AdminRoleAddHandler,
    AdminRoleUpdateHandler,
    AdminRoleDeleteHandler,
    AdminRolePermissionsHandler,
    AdminRoleAllPermissionsHandler
)
from app.controllers.admin_model import (
    AdminModelHandler,
    AdminModelListHandler,
    AdminModelDetailHandler,
    AdminModelAddHandler,
    AdminModelUpdateHandler,
    AdminModelDeleteHandler,
    AdminModelDefaultHandler,
    AdminModelStatsHandler,
    AdminModelTestHandler,
    AdminModelStreamTestHandler
)
from app.controllers.admin_lookout import (
    AdminLookoutSourceHandler,
    AdminLookoutWorkbenchHandler,
    AdminLookoutSourceListHandler,
    AdminLookoutSourceOptionsHandler,
    AdminLookoutSourceAddHandler,
    AdminLookoutSourceUpdateHandler,
    AdminLookoutSourceDeleteHandler,
    AdminLookoutCollectHandler,
    AdminLookoutTaskListHandler,
    AdminDataWarehouseHandler,
    AdminDataWarehouseDetailPageHandler,
    AdminDataWarehouseListHandler,
    AdminDataWarehouseDetailHandler,
    AdminDataWarehouseDeleteHandler,
    AdminDataWarehouseBatchDeleteHandler,
    AdminDataWarehouseDeepCollectHandler,
    AdminDataWarehouseDeepTaskHandler,
    AdminDataWarehouseDeepLogsHandler
)

# 引入数据库初始化方法
from app.models.db import init_db


def make_app():
    base_url = os.path.dirname(os.path.abspath(__file__))

    settings = dict(
        # 预留 view 层的配置
        template_path=os.path.join(base_url, "app", "templates"),
        static_path=os.path.join(base_url, "app", "static"),

        # cookie 配置
        cookie_secret="demp-cookie-secret-change-wayne",

        # 登录跳转地址
        login_url="/auth/login",

        # 开启 xsrf 防护
        xsrf_cookies=True,

        # 开发模式
        debug=True,
        autoreload=True
    )

    return tornado.web.Application([
        # 用户侧路由
        (r"/", IndexHandler),
        (r"/auth/login", LoginHandler),
        (r"/auth/logout", LogoutHandler),

        # 后台管理路由
        (r"/admin/", AdminIndexHandler),
        (r"/admin/auth/login", AdminLoginHandler),
        (r"/admin/auth/logout", AdminLogoutHandler),
        (r"/admin/user", AdminUserHandler),
        (r"/admin/api/user/list", AdminUserListHandler),
        (r"/admin/api/user/add", AdminUserAddHandler),
        (r"/admin/api/user/update", AdminUserUpdateHandler),
        (r"/admin/api/user/delete", AdminUserDeleteHandler),
        (r"/admin/api/user/batch-delete", AdminUserBatchDeleteHandler),
        (r"/admin/api/stats", AdminStatsHandler),

        # 权限管理路由
        (r"/admin/permission", AdminPermissionHandler),
        (r"/admin/api/permission/list", AdminPermissionListHandler),
        (r"/admin/api/permission/tree", AdminPermissionTreeHandler),
        (r"/admin/api/permission/add", AdminPermissionAddHandler),
        (r"/admin/api/permission/update", AdminPermissionUpdateHandler),
        (r"/admin/api/permission/delete", AdminPermissionDeleteHandler),
        (r"/admin/api/permission/menus", AdminPermissionMenusHandler),

        # 角色管理路由
        (r"/admin/role", AdminRoleHandler),
        (r"/admin/api/role/list", AdminRoleListHandler),
        (r"/admin/api/role/add", AdminRoleAddHandler),
        (r"/admin/api/role/update", AdminRoleUpdateHandler),
        (r"/admin/api/role/delete", AdminRoleDeleteHandler),
        (r"/admin/api/role/permissions", AdminRolePermissionsHandler),
        (r"/admin/api/role/all-permissions", AdminRoleAllPermissionsHandler),

        # 模型引擎路由
        (r"/admin/model", AdminModelHandler),
        (r"/admin/api/model/list", AdminModelListHandler),
        (r"/admin/api/model/detail", AdminModelDetailHandler),
        (r"/admin/api/model/add", AdminModelAddHandler),
        (r"/admin/api/model/update", AdminModelUpdateHandler),
        (r"/admin/api/model/delete", AdminModelDeleteHandler),
        (r"/admin/api/model/default", AdminModelDefaultHandler),
        (r"/admin/api/model/stats", AdminModelStatsHandler),
        (r"/admin/api/model/test", AdminModelTestHandler),
        (r"/admin/api/model/test-stream", AdminModelStreamTestHandler),

        # 智能瞭望与数据管理路由
        (r"/admin/lookout/source", AdminLookoutSourceHandler),
        (r"/admin/lookout/collect", AdminLookoutWorkbenchHandler),
        (r"/admin/api/lookout/source/list", AdminLookoutSourceListHandler),
        (r"/admin/api/lookout/source/options", AdminLookoutSourceOptionsHandler),
        (r"/admin/api/lookout/source/add", AdminLookoutSourceAddHandler),
        (r"/admin/api/lookout/source/update", AdminLookoutSourceUpdateHandler),
        (r"/admin/api/lookout/source/delete", AdminLookoutSourceDeleteHandler),
        (r"/admin/api/lookout/collect", AdminLookoutCollectHandler),
        (r"/admin/api/lookout/source/collect", AdminLookoutCollectHandler),
        (r"/admin/api/lookout/task/list", AdminLookoutTaskListHandler),
        (r"/admin/data/warehouse", AdminDataWarehouseHandler),
        (r"/admin/data/warehouse/detail", AdminDataWarehouseDetailPageHandler),
        (r"/admin/api/data/warehouse/list", AdminDataWarehouseListHandler),
        (r"/admin/api/data/warehouse/detail", AdminDataWarehouseDetailHandler),
        (r"/admin/api/data/warehouse/delete", AdminDataWarehouseDeleteHandler),
        (r"/admin/api/data/warehouse/batch-delete", AdminDataWarehouseBatchDeleteHandler),
        (r"/admin/api/data/warehouse/deep-collect", AdminDataWarehouseDeepCollectHandler),
        (r"/admin/api/data/warehouse/deep-task", AdminDataWarehouseDeepTaskHandler),
        (r"/admin/api/data/warehouse/deep-logs", AdminDataWarehouseDeepLogsHandler),
    ], **settings)


if __name__ == "__main__":
    # 启动服务前，初始化数据库
    init_db()

    app = make_app()
    server = HTTPServer(app)

    server.bind(10086)

    # Windows 下不能用 start(0)，这里用 1
    server.start(1)

    print("====== Server Start ====== : 10086 ======", flush=True)

    tornado.ioloop.IOLoop.current().start()
