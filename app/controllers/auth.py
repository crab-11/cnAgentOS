# 认证相关 controller（登录/注册/退出）

import tornado.web

from app.controllers.base import BaseHandler
from app.models.user import UserRepository


class LoginHandler(BaseHandler):
    # /auth/login
    def get(self):
        self.render("login.html", title="登录", error=None)

    def post(self):
        username = (self.get_body_argument("username", "") or "").strip()
        password = self.get_body_argument("password", "")

        if not username or not password:
            self.set_status(400)
            return self.render(
                "login.html",
                title="登录",
                error="用户名或密码不能为空或输入了无效数据"
            )

        if not UserRepository.verify_user(username, password):
            self.set_status(401)
            return self.render(
                "login.html",
                title="登录",
                error="用户名或密码错误"
            )

        self.set_secure_cookie("username", username)
        self.redirect("/")


class LogoutHandler(BaseHandler):
    # /auth/logout
    def post(self):
        self.clear_cookie("username")
        self.redirect("/auth/login")