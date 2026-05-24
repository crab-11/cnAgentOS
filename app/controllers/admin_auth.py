# 后台管理认证控制器

import tornado.web
from app.controllers.base import BaseHandler
from app.models.user import UserRepository


class AdminBaseHandler(BaseHandler):
    def get_current_user(self):
        username = self.get_secure_cookie("admin_username")
        if not username:
            return None
        return username.decode("utf-8")
    
    def get_login_url(self):
        return "/admin/auth/login"


class AdminLoginHandler(AdminBaseHandler):
    def get(self):
        if self.current_user:
            self.redirect("/admin/")
            return
        self.render("admin_login.html", title="管理后台登录", error=None)

    def post(self):
        username = (self.get_body_argument("username", "") or "").strip()
        password = self.get_body_argument("password", "")

        if not username or not password:
            self.set_status(400)
            return self.render(
                "admin_login.html",
                title="管理后台登录",
                error="用户名或密码不能为空"
            )

        user = UserRepository.get_user_by_username(username)
        if not user or not UserRepository.verify_user(username, password):
            self.set_status(401)
            return self.render(
                "admin_login.html",
                title="管理后台登录",
                error="用户名或密码错误"
            )

        if user["status"] != 1:
            self.set_status(403)
            return self.render(
                "admin_login.html",
                title="管理后台登录",
                error="该账户已被禁用，请联系管理员"
            )

        remember = self.get_body_argument("remember", None)
        expires_days = 7 if remember else None

        UserRepository.update_last_login(username)
        self.set_secure_cookie("admin_username", username, expires_days=expires_days)
        self.redirect("/admin/")


class AdminLogoutHandler(AdminBaseHandler):
    def get(self):
        self.clear_cookie("admin_username")
        self.redirect("/admin/auth/login")

    def post(self):
        self.clear_cookie("admin_username")
        self.redirect("/admin/auth/login")
