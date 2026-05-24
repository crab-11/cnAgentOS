# 初始化默认管理员账户
# 运行方式：python init_admin.py

from app.models.db import init_db
from app.models.user import UserRepository

def init_admin():
    print("开始初始化数据库...")
    init_db()
    
    admin_username = "admin"
    admin_password = "admin888"
    
    user = UserRepository.get_user_by_username(admin_username)
    
    if user:
        UserRepository.update_user(
            user_id=user["id"],
            username=admin_username,
            nickname="系统管理员",
            email="admin@example.com",
            password=admin_password,
            status=1
        )
        UserRepository.ensure_user_role(admin_username, "admin")
        print(f"管理员账户已存在，已重置为默认密码: {admin_username}")
    else:
        success = UserRepository.create_user(
            admin_username,
            admin_password,
            role="admin",
            status=1,
            nickname="系统管理员",
            email="admin@example.com"
        )
        if success:
            UserRepository.ensure_user_role(admin_username, "admin")
            print(f"管理员账户创建成功!")
            print(f"用户名: {admin_username}")
            print(f"密码: {admin_password}")
            print(f"后台登录地址: http://localhost:10086/admin/auth/login")
        else:
            print("管理员账户创建失败")

if __name__ == "__main__":
    init_admin()
