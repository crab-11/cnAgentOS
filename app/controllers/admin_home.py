# 后台主页控制器

import tornado.web
from app.controllers.admin_auth import AdminBaseHandler
from app.models.user import UserRepository


class AdminIndexHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin_index.html", title="后台控制台", username=self.current_user)
