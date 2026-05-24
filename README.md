# cnAgentOS - AI智能瞭望与智能问数系统

## 项目概述

cnAgentOS 是一个基于 Python Tornado 框架开发的 Web 应用系统，采用 MVC（Model-View-Controller）架构模式，B/S（浏览器/服务器）模式部署。本项目旨在构建一套 AI 智能瞭望与智能问数系统，提供智能化的数据分析和可视化服务。

## 技术栈

| 技术分类 | 技术选型 | 版本/说明 |
|---------|---------|----------|
| 编程语言 | Python | 3.11 |
| Web框架 | Tornado | 6.5.5 |
| 数据库 | SQLite3 | 内置轻量级数据库 |
| 前端技术 | HTML5 | 语义化标签 |
| 样式技术 | CSS | 基础样式表 |
| 脚本语言 | JavaScript | 原生 JS |
| 前端 UI 框架 | Layui | 2.13.6 (本地化) |
| 响应式框架 | Bootstrap | 5.3.8 (本地化) |
| 图标库 | Font Awesome | 5.15.4 (本地化) |
| 虚拟环境 | venv | Python 内置虚拟环境管理 |

## 项目目录结构

```
cnAgentOS/
├── app.md                    # 项目目录结构说明文档
├── main.py                   # 程序主入口，Tornado MVC 架构核心
├── test.py                   # 单元测试脚本，用于模块/包/方法测试
├── README.md                 # 项目说明文档（本文件）
│
├── app/                      # 主包目录
│   ├── __init__.py           # 包初始化文件
│   │
│   ├── controllers/          # MVC 控制层
│   │   ├── __init__.py       # 控制器包初始化
│   │   ├── auth.py           # 鉴权控制器（登录、注册、退出）
│   │   ├── base.py           # 基础控制器（公共逻辑）
│   │   └── home.py           # 首页控制器
│   │
│   ├── models/               # 业务与数据模型层
│   │   ├── __init__.py       # 模型包初始化
│   │   ├── db.py             # SQLite 数据库访问层
│   │   └── user.py           # 用户数据模型（UserRepository）
│   │
│   ├── static/               # 静态资源目录（View 层）
│   │   ├── css/
│   │   │   └── base.css      # 基础样式表
│   │   ├── js/
│   │   │   └── base.js       # 基础 JavaScript 脚本
│   │   └── libs/             # 第三方前端组件库（本地化）
│   │       ├── layui-v2.13.6/       # Layui UI 框架
│   │       ├── bootstrap-5.3.8-dist/ # Bootstrap 响应式框架
│   │       └── fontawesome-free-5.15.4-web/ # Font Awesome 图标库
│   │
│   └── templates/            # HTML 模板目录（View 层）
│       ├── base.html         # 基础模板（布局框架）
│       ├── index.html        # 后台首页模板
│       ├── login.html        # 登录页模板
│       └── register.html     # 注册页模板
│
├── database/                 # SQLite 数据库文件目录
│   └── app.db                # 自动创建的 SQLite 数据库文件
│
└── venv/                     # Python 虚拟环境目录
    └── (虚拟环境文件)
```

## 架构设计

### MVC 三层架构

本项目采用经典的 MVC（Model-View-Controller）三层架构设计：

```
┌─────────────────────────────────────────────────────────────┐
│                        浏览器客户端 (B/S)                     │
├─────────────────────────────────────────────────────────────┤
│                          HTTP 请求                           │
├─────────────────────────────────────────────────────────────┤
│                    Controller 控制层                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  auth.py    │  │  home.py    │  │      base.py        │ │
│  │ 登录/注册/退出│  │  首页处理   │  │  基础公共逻辑处理   │ │
│  └─────┬───────┘  └─────┬───────┘  └────────────┬────────┘ │
├────────┼─────────────────┼───────────────────────┼─────────┤
│        │                 │                       │         │
│  ┌─────▼─────────────────▼───────────────────────▼───────┐ │
│  │                    Model 模型层                       │ │
│  │  ┌─────────────────────────┐  ┌────────────────────┐ │ │
│  │  │      db.py              │  │     user.py        │ │ │
│  │  │  数据库连接与初始化     │  │  用户数据模型      │ │ │
│  │  └─────────────────────────┘  └────────────────────┘ │ │
│  └───────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    View 视图层                               │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │ base.html    │  │ login.html   │  │   index.html      │ │
│  │ 基础模板     │  │ 登录页模板   │  │  后台首页模板     │ │
│  └──────────────┘  └──────────────┘  └───────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    数据库层                                  │
│                    SQLite3 (app.db)                          │
└─────────────────────────────────────────────────────────────┘
```

### 架构特点

1. **分离关注点**：MVC 架构将业务逻辑、数据展示和用户交互分离
2. **可维护性**：模块化设计便于代码维护和扩展
3. **可扩展性**：支持后续添加新的控制器、模型和视图
4. **安全性**：内置 XSRF 防护、密码加密、Cookie 加密等安全机制

## 核心模块说明

### 1. 主入口 (main.py)

**职责**：应用程序启动入口，Tornado 服务器配置和路由定义

**关键配置**：
- **服务器端口**：10086
- **模板路径**：`app/templates`
- **静态资源路径**：`app/static`
- **Cookie 密钥**：已配置（生产环境需更换）
- **登录跳转 URL**：`/auth/login`
- **调试模式**：已开启（debug=True, autoreload=True）

**路由表**：
| 路由路径 | 处理器 | 请求方法 | 说明 |
|---------|--------|---------|------|
| `/` | IndexHandler | GET | 后台首页（需登录） |
| `/auth/login` | LoginHandler | GET/POST | 登录页面 |
| `/auth/logout` | LogoutHandler | POST | 退出登录 |

### 2. 控制层 (controllers)

#### 2.1 base.py - 基础控制器

**职责**：提供所有控制器的公共基类

**核心功能**：
- `get_current_user()` 方法：获取当前登录用户状态
- 返回 `username` 字符串或 `None`
- 配合 `@tornado.web.authenticated` 装饰器实现登录态校验

**工作原理**：
```
请求到达 → 检查 secure cookie → 返回 username/None → 框架判断是否跳转登录页
```

#### 2.2 auth.py - 鉴权控制器

**LoginHandler（登录处理器）**：
- **GET 请求**：渲染登录页面，显示登录表单
- **POST 请求**：
  1. 接收用户名和密码参数
  2. 参数校验（非空检查）
  3. 调用 `UserRepository.verify_user()` 验证凭据
  4. 验证成功：设置 secure cookie 并跳转到首页
  5. 验证失败：显示错误信息并返回相应 HTTP 状态码

**LogoutHandler（退出处理器）**：
- **POST 请求**：清除 cookie 并重定向到登录页

#### 2.3 home.py - 首页控制器

**IndexHandler（首页处理器）**：
- **GET 请求**：
  - 使用 `@tornado.web.authenticated` 装饰器保护
  - 未登录用户自动跳转到登录页
  - 已登录用户渲染后台首页模板，传递用户名

### 3. 模型层 (models)

#### 3.1 db.py - 数据库访问层

**职责**：SQLite 数据库连接管理和表初始化

**核心方法**：
- `_project_root()`：获取项目根目录路径
- `get_connection()`：获取数据库连接（自动创建目录）
  - 设置 `row_factory = sqlite3.Row` 支持字典式访问
- `init_db()`：数据库初始化（创建 users 表）

**数据库表结构 - users**：
| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 用户ID |
| username | TEXT | NOT NULL UNIQUE | 用户名（唯一） |
| password_hash | TEXT | NOT NULL | 密码哈希值 |
| salt | TEXT | NOT NULL | 密码盐值 |
| create_at | TEXT | DEFAULT(datetime('now')) | 创建时间 |

#### 3.2 user.py - 用户数据模型

**职责**：用户数据的 CRUD 操作和密码管理

**核心类**：`UserRepository`

**静态方法**：

1. **`create_user(username, password)`**：
   - 生成随机盐值（16 字节）
   - 使用 PBKDF2-HMAC-SHA256 算法加密密码
   - 插入数据库
   - 返回：创建成功返回 True，用户名冲突返回 False

2. **`get_user_by_username(username)`**：
   - 根据用户名查询用户信息
   - 返回：用户记录字典或 None

3. **`verify_user(username, password)`**：
   - 查询用户信息
   - 使用存储的盐值重新计算密码哈希
   - 比对哈希值
   - 返回：验证成功返回 True，否则返回 False

**密码加密机制**：
```
密码 + 随机盐值 → PBKDF2-HMAC-SHA256 (100,000 次迭代) → 十六进制哈希值
```

### 4. 视图层 (templates & static)

#### 4.1 模板文件 (templates)

**base.html（基础模板）**：
- 提供 HTML5 基础结构
- 引入公共 CSS 和 JS 资源
- 定义 `{% block body %}{% end %}` 区块供子模板继承
- 使用 Tornado 模板引擎语法

**login.html（登录页）**：
- 继承 base.html 基础模板
- 显示错误信息（如有）
- 包含登录表单（用户名、密码输入框）
- 内置 XSRF 防护 token
- 表单提交方法：POST 到 `/auth/login`

**index.html（后台首页）**：
- 继承 base.html 基础模板
- 显示当前登录用户名
- 提供退出登录按钮
- 表单提交方法：POST 到 `/auth/logout`

**register.html（注册页）**：
- 文件已创建（待实现注册功能）

#### 4.2 静态资源 (static)

**base.css**：
- CSS 基础重置样式
- 清除默认 margin 和 padding
- 设置 html/body 宽高为 100%
- 定义错误提示样式（红色文字）

**base.js**：
- 基础 JavaScript 脚本文件
- 当前包含页面加载日志输出
- 预留公共 JS 函数扩展位置

## 已实现功能

### ✅ 登录功能（已验证通过）

**功能描述**：
- 用户通过用户名和密码登录系统
- 登录成功后跳转到后台首页
- 未登录用户访问受保护页面自动跳转到登录页
- 支持安全退出功能

**技术实现**：
1. **前端**：HTML 表单 + POST 请求
2. **安全**：XSRF 防护 + Secure Cookie + 密码哈希
3. **后端**：Tornado RequestHandler + SQLite 查询
4. **验证**：PBKDF2-HMAC-SHA256 密码验证

**使用流程**：
```
1. 启动服务 → 访问 http://localhost:10086
2. 自动跳转到登录页 → 输入用户名和密码
3. 提交登录 → 后端验证 → 验证成功设置 cookie → 跳转到首页
4. 首页显示用户名 → 可点击退出按钮 → 清除 cookie → 返回登录页
```

**测试方法**：
```bash
# 运行测试脚本（创建测试用户并验证登录）
python test.py

# 启动服务
python main.py

# 访问登录页
浏览器打开 http://localhost:10086/auth/login
```

## 安全机制

| 安全特性 | 实现方式 | 说明 |
|---------|---------|------|
| XSRF 防护 | `xsrf_cookies=True` | 所有 POST 请求自动验证 XSRF token |
| Cookie 加密 | `cookie_secret` | Secure Cookie 使用密钥签名 |
| 密码加密 | PBKDF2-HMAC-SHA256 | 100,000 次迭代 + 随机盐值 |
| 登录态保护 | `@tornado.web.authenticated` | 路由级登录校验 |
| SQL 注入防护 | 参数化查询 | `?` 占位符方式 |

## 开发规范

### 代码规范
1. **MVC 分层**：严格遵循 MVC 架构，不跨层调用
2. **命名规范**：
   - 文件名：小写 + 下划线
   - 类名：大驼峰（PascalCase）
   - 方法名：小写 + 下划线
   - 私有方法：前缀下划线（如 `_hash_password`）
3. **注释规范**：文件头部说明职责，关键逻辑添加注释

### 数据库规范
1. **数据库访问**：统一通过 `db.py` 获取连接
2. **SQL 写法**：使用参数化查询，禁止字符串拼接
3. **表命名**：复数形式（如 `users`）

### 前端规范
1. **模板继承**：所有页面继承 `base.html`
2. **静态资源**：使用 `static_url()` 方法引用
3. **表单安全**：所有 POST 表单必须包含 `{% module xsrf_form_html() %}`
4. **第三方组件**：必须本地化引用，禁止使用 CDN
5. **组件使用原则**：
   - 后台管理页面优先使用 Layui 框架
   - 用户侧页面可使用 Bootstrap 布局
   - 全局图标统一使用 Font Awesome

### 前端组件引用示例
```html
<!-- Layui 引用示例 -->
<link rel="stylesheet" href="{{ static_url('libs/layui-v2.13.6/layui.css') }}">
<script src="{{ static_url('libs/layui-v2.13.6/layui.js') }}"></script>

<!-- Bootstrap 引用示例 -->
<link rel="stylesheet" href="{{ static_url('libs/bootstrap-5.3.8-dist/css/bootstrap.min.css') }}">
<script src="{{ static_url('libs/bootstrap-5.3.8-dist/js/bootstrap.bundle.min.js') }}"></script>

<!-- Font Awesome 引用示例 -->
<link rel="stylesheet" href="{{ static_url('libs/fontawesome-free-5.15.4-web/css/all.min.css') }}">
```

## 环境搭建与运行

### 前置要求
- Python 3.11 已安装
- 虚拟环境工具（venv）

### 环境配置步骤
```bash
# 1. 进入项目目录
cd cnAgentOS

# 2. 创建虚拟环境（如尚未创建）
python -m venv venv

# 3. 激活虚拟环境（Windows PowerShell）
.\venv\Scripts\Activate.ps1

# 4. 安装依赖
pip install tornado==6.5.5

# 5. 运行测试脚本（可选）
python test.py

# 6. 启动服务
python main.py

# 7. 浏览器访问
http://localhost:10086
```

## 待开发功能

### 🚧 注册功能（已预留）
- 注册页面模板已创建（`register.html`）
- `UserRepository.create_user()` 方法已实现
- 需在 `auth.py` 中补充注册路由处理逻辑

### 🚧 AI 智能瞭望系统
- 数据监控面板
- 实时数据可视化
- 异常数据预警

### 🚧 智能问数系统
- 自然语言查询接口
- AI 数据分析师
- 报表自动生成

## 后续开发指南

### 新增控制器
```python
# 1. 在 controllers/ 下创建新文件
from app.controllers.base import BaseHandler

class NewHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("new_page.html", title="新页面")
```

### 新增路由
```python
# 在 main.py 的 make_app() 中添加路由
from app.controllers.new_module import NewHandler

return tornado.web.Application([
    (r"/", IndexHandler),
    (r"/auth/login", LoginHandler),
    (r"/auth/logout", LogoutHandler),
    (r"/new-page", NewHandler),  # 新增路由
], **settings)
```

### 新增模型
```python
# 1. 在 models/ 下创建新文件
from app.models.db import get_connection

class NewModel:
    @staticmethod
    def get_data():
        with get_connection() as conn:
            return conn.execute("SELECT * FROM table").fetchall()

# 2. 在 db.py 的 init_db() 中添加建表语句
```

### 新增视图
```html
<!-- 1. 在 templates/ 下创建新模板 -->
{% extends "base.html" %}
{% block body %}
<h3>新页面</h3>
{% end %}

<!-- 2. 在 static/css/ 或 static/js/ 中添加专属资源 -->
```

## 注意事项

1. **生产环境配置**：
   - 更换 `cookie_secret` 为强密钥
   - 关闭 `debug` 和 `autoreload`
   - 使用 HTTPS
   - 考虑使用生产级数据库（MySQL/PostgreSQL）

2. **数据库备份**：
   - 定期备份 `database/app.db`
   - 可使用 SQLite 导出工具进行数据迁移

3. **扩展建议**：
   - 可添加日志模块（Python logging）
   - 可添加错误处理中间件
   - 可添加 API 版本控制
   - 可考虑引入 ORM（如 SQLAlchemy）

## 项目状态

| 模块 | 状态 | 备注 |
|-----|------|------|
| 基础架构 | ✅ 完成 | MVC + B/S 架构已搭建 |
| 数据库层 | ✅ 完成 | SQLite + 用户表已实现 |
| 用户模型 | ✅ 完成 | 增查验功能已实现 |
| 登录功能 | ✅ 完成 | 已验证通过 |
| 注册功能 | 🚧 待开发 | 模型已就绪，控制器待实现 |
| 后台首页 | ✅ 完成 | 基础页面已实现 |
| AI 瞭望系统 | 📋 待规划 | 核心业务功能 |
| 智能问数系统 | 📋 待规划 | 核心业务功能 |

---

**项目创建时间**：2026-05-23  
**技术负责人**：开发团队  
**文档版本**：v1.0
