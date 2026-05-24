# cnAgentOS - AI智能瞭望与智能问数系统

## 项目概述

cnAgentOS 是一个基于 Python Tornado 框架开发的 Web 应用系统，采用 MVC 分层架构和 B/S 部署模式。当前阶段重点完成了后端管理侧基础能力，包括后台登录、后台管理框架、系统管理下的用户管理、角色管理、功能管理，以及用户角色设置和角色功能授权。

## 技术栈

| 技术分类 | 技术选型 | 版本/说明 |
|---------|---------|----------|
| 编程语言 | Python | 3.11/3.12 可运行 |
| Web框架 | Tornado | 6.5.5 |
| 数据库 | SQLite3 | 内置轻量级数据库 |
| 架构模式 | MVC | Controller / Model / Template |
| 前端 UI | Layui | 2.13.6，本地化 |
| 响应式框架 | Bootstrap | 5.3.8，本地化 |
| 图标库 | Font Awesome | 5.15.4，本地化 |

## 快速启动

```powershell
cd cnAgentOS
pip install tornado==6.5.5
python init_admin.py
python main.py
```

访问地址：

- 用户侧入口：`http://localhost:10086/`
- 后台登录：`http://localhost:10086/admin/auth/login`
- 默认管理员：`admin / admin888`

`init_admin.py` 会确保默认管理员账号存在、启用，并绑定“超级管理员”角色。

## 当前功能

### 用户侧基础功能

- 用户登录
- 用户退出
- Secure Cookie 登录态
- XSRF 防护
- 密码 PBKDF2-HMAC-SHA256 加盐哈希

### 后台管理框架

- 独立后台登录页
- Layui 风格后台布局
- 左侧菜单、右侧工作区
- 管理员头像与退出入口
- 统一 XSRF AJAX 请求头处理
- 后台主页/控制台预留

### 用户管理

- 用户列表分页，默认每页 20 条
- 用户列表展示用户名、昵称、邮箱、角色、状态、最后登录时间、创建时间
- 支持按用户名和状态筛选
- 用户新增
- 用户修改
- 用户删除
- 批量删除
- 用户状态启用/禁用
- 新增/编辑用户时填写用户名、昵称、邮箱、密码并分配角色
- `admin` 为系统默认用户：
  - 角色固定为“超级管理员”
  - 不能删除
  - 不能修改用户名、状态、角色
  - 只能修改密码

### 角色管理

- 默认内置角色：
  - `admin`：超级管理员，系统角色
  - `user`：普通用户
- 角色新增
- 角色修改
- 角色删除
- 角色启用/禁用
- 角色分页查询
- 系统角色不能修改和删除
- 新增/编辑角色时填写角色标识、角色名称、备注，并勾选可访问的功能权限

### 功能管理

- 树形结构展示功能菜单
- 内置顶级功能：首页、系统管理、智能瞭望、模型管理、数据管理、系统设置
- 系统管理包含用户管理、角色管理、功能管理三个子模块
- 支持功能节点新增、编辑、删除
- 功能类型：
  - 分组
  - 菜单
- 支持功能名称、功能标识、父级节点、访问路径、排序号、图标、状态
- 角色与功能权限映射
- 权限树用于角色权限配置
- 功能管理主要用于角色权限分配引用，不直接面向普通用户操作

## 主要目录结构

```text
cnAgentOS/
├── main.py                         # Tornado 服务入口和路由配置
├── init_admin.py                   # 默认管理员初始化脚本
├── README.md                       # 项目说明
├── requirements.md                 # 需求追踪文档
├── app/
│   ├── controllers/
│   │   ├── auth.py                 # 用户侧登录/退出
│   │   ├── home.py                 # 用户侧首页
│   │   ├── base.py                 # 通用 Handler
│   │   ├── admin_auth.py           # 后台登录/退出/后台基类
│   │   ├── admin_home.py           # 后台首页
│   │   ├── admin_user.py           # 后台用户管理
│   │   ├── admin_role.py           # 后台角色管理
│   │   └── admin_permission.py     # 后台功能管理
│   ├── models/
│   │   ├── db.py                   # SQLite 连接和初始化
│   │   ├── user.py                 # 用户模型
│   │   ├── role.py                 # 角色模型
│   │   └── permission.py           # 功能/权限模型
│   ├── templates/
│   │   ├── admin_login.html        # 后台登录页
│   │   ├── admin_base.html         # 后台基础布局
│   │   ├── admin_index.html        # 后台首页
│   │   ├── admin_user.html         # 用户管理页
│   │   ├── admin_role.html         # 角色管理页
│   │   └── admin_permission.html   # 功能管理页
│   └── static/
│       ├── images/
│       └── libs/                   # Layui / Bootstrap / Font Awesome
└── database/
    └── app.db                      # SQLite 数据库文件
```

## 核心路由

### 用户侧

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 用户侧首页 |
| `/auth/login` | GET/POST | 用户侧登录 |
| `/auth/logout` | POST | 用户侧退出 |

### 后台管理侧

| 路由 | 方法 | 说明 |
|------|------|------|
| `/admin/` | GET | 后台首页 |
| `/admin/auth/login` | GET/POST | 后台登录 |
| `/admin/auth/logout` | GET/POST | 后台退出 |
| `/admin/user` | GET | 用户管理页面 |
| `/admin/api/user/list` | GET | 用户列表 |
| `/admin/api/user/add` | POST | 新增用户 |
| `/admin/api/user/update` | POST | 修改用户 |
| `/admin/api/user/delete` | POST | 删除用户 |
| `/admin/api/user/batch-delete` | POST | 批量删除用户 |
| `/admin/role` | GET | 角色管理页面 |
| `/admin/api/role/list` | GET | 角色列表 |
| `/admin/api/role/add` | POST | 新增角色 |
| `/admin/api/role/update` | POST | 修改角色 |
| `/admin/api/role/delete` | POST | 删除角色 |
| `/admin/api/role/permissions` | GET/POST | 查询/保存角色权限 |
| `/admin/api/role/all-permissions` | GET | 获取权限树 |
| `/admin/permission` | GET | 功能管理页面 |
| `/admin/api/permission/list` | GET | 功能列表 |
| `/admin/api/permission/tree` | GET | 功能树 |
| `/admin/api/permission/add` | POST | 新增功能 |
| `/admin/api/permission/update` | POST | 修改功能 |
| `/admin/api/permission/delete` | POST | 删除功能 |

## 数据库表

| 表名 | 说明 |
|------|------|
| `users` | 用户账号、昵称、邮箱、密码哈希、状态、最后登录时间、兼容角色字段 |
| `roles` | 角色定义 |
| `permissions` | 功能/菜单/权限定义 |
| `role_permissions` | 角色与功能权限映射 |
| `user_roles` | 用户与角色映射 |

## 安全机制

| 安全特性 | 实现方式 |
|---------|---------|
| 密码安全 | PBKDF2-HMAC-SHA256 + 随机盐 |
| 登录态 | Tornado Secure Cookie |
| XSRF | `xsrf_cookies=True` + 表单 token + AJAX Header |
| SQL 注入防护 | SQLite 参数化查询 |
| 系统账号保护 | 后端强制保护 `admin` 用户 |
| 系统角色保护 | 后端强制保护系统角色 |

## 开发规范

1. 控制层放在 `app/controllers/`。
2. 数据访问和业务模型放在 `app/models/`。
3. 页面模板放在 `app/templates/`。
4. 静态资源放在 `app/static/`。
5. 后台页面优先使用 Layui。
6. 所有第三方前端资源必须本地化引用，不使用 CDN。
7. 所有写操作接口必须携带 XSRF token。
8. 数据库访问统一通过 `app.models.db.get_connection()`。

## 当前项目状态

| 模块 | 状态 | 备注 |
|------|------|------|
| 基础架构 | 已完成 | Tornado + MVC + SQLite |
| 用户侧登录 | 已完成 | 登录/退出/登录态 |
| 后台登录页 | 已完成 | 参考 Kuboard 风格重做 |
| 后台管理框架 | 已完成 | 左侧菜单、右侧工作区 |
| 用户管理 | 已完成 | 增删改查、批量删除、分页、状态筛选、角色设置 |
| 用户角色显示 | 已完成 | 列表显示真实角色、昵称、邮箱、最后登录时间 |
| 默认 admin 保护 | 已完成 | 不能删改资料，只能改密码 |
| 角色管理 | 已完成 | 增删改查、状态维护、系统角色保护、功能权限勾选 |
| 功能管理 | 已完成 | 树形功能维护、权限树、角色映射 |
| 后台首页 | 预留 | 后续模块完成后统一完善 |
| 智能问数 | 待规划 | 后续核心业务 |
| AI 智能瞭望 | 待规划 | 后续核心业务 |

## 后续建议

- 将左侧菜单从静态模板进一步改造成按角色权限动态渲染。
- 增加接口级权限校验。
- 完善注册功能或明确移除注册入口。
- 增加用户操作日志。
- 后续业务模块可继续接入数字员工、模型管理、智能瞭望、数据管理等能力。

---

**文档更新时间**：2026-05-24  
**文档版本**：v1.3
