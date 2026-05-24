# 数据库链接与建表
import os
import sqlite3


# 获得项目根路径的方法
def _project_root():
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )

# 获得数据库文件路径
DB_PATH = os.path.join(_project_root(), "database", "app.db")

# 获得数据库连接
def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

#
def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users(
                id integer PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                nickname TEXT,
                email TEXT,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                status INTEGER NOT NULL DEFAULT 1,
                last_login_at TEXT,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )

        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'role' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")

        if 'status' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN status INTEGER NOT NULL DEFAULT 1")

        if 'nickname' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN nickname TEXT")

        if 'email' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")

        if 'last_login_at' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN last_login_at TEXT")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS permissions(
                id integer PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                code TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL DEFAULT 'menu',
                parent_id INTEGER DEFAULT 0,
                icon TEXT,
                url TEXT,
                sort_order INTEGER DEFAULT 0,
                status INTEGER DEFAULT 1,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS roles(
                id integer PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                description TEXT,
                is_system INTEGER DEFAULT 0,
                status INTEGER DEFAULT 1,
                create_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )

        cursor = conn.execute("PRAGMA table_info(roles)")
        role_columns = [row[1] for row in cursor.fetchall()]
        
        if 'is_system' not in role_columns:
            conn.execute("ALTER TABLE roles ADD COLUMN is_system INTEGER DEFAULT 0")
        
        if 'status' not in role_columns:
            conn.execute("ALTER TABLE roles ADD COLUMN status INTEGER DEFAULT 1")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS role_permissions(
                id integer PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                permission_id INTEGER NOT NULL,
                create_at TEXT NOT NULL DEFAULT(datetime('now')),
                FOREIGN KEY(role_id) REFERENCES roles(id) ON DELETE CASCADE,
                FOREIGN KEY(permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
                UNIQUE(role_id, permission_id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_roles(
                id integer PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                create_at TEXT NOT NULL DEFAULT(datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(role_id) REFERENCES roles(id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS model_services(
                id integer PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                provider TEXT NOT NULL,
                endpoint_url TEXT NOT NULL,
                api_key TEXT NOT NULL,
                model_name TEXT NOT NULL,
                temperature REAL NOT NULL DEFAULT 0.7,
                max_tokens INTEGER NOT NULL DEFAULT 1024,
                stream_enabled INTEGER NOT NULL DEFAULT 1,
                is_default INTEGER NOT NULL DEFAULT 0,
                status INTEGER NOT NULL DEFAULT 1,
                remark TEXT,
                create_at TEXT NOT NULL DEFAULT(datetime('now')),
                update_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS model_call_logs(
                id integer PRIMARY KEY AUTOINCREMENT,
                service_id INTEGER,
                model_name TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                latency_ms INTEGER NOT NULL DEFAULT 0,
                success INTEGER NOT NULL DEFAULT 1,
                error_message TEXT,
                create_at TEXT NOT NULL DEFAULT(datetime('now')),
                FOREIGN KEY(service_id) REFERENCES model_services(id) ON DELETE SET NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lookout_sources(
                id integer PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                source_type TEXT NOT NULL DEFAULT 'website',
                target_url TEXT NOT NULL,
                request_method TEXT NOT NULL DEFAULT 'GET',
                parser_type TEXT NOT NULL DEFAULT 'html',
                request_headers TEXT,
                default_params TEXT,
                param_config TEXT,
                extract_rules TEXT,
                page_param TEXT NOT NULL DEFAULT 'pn',
                page_step INTEGER NOT NULL DEFAULT 10,
                keyword_param TEXT NOT NULL DEFAULT 'word',
                keywords TEXT,
                status INTEGER NOT NULL DEFAULT 1,
                last_collected_at TEXT,
                remark TEXT,
                create_at TEXT NOT NULL DEFAULT(datetime('now')),
                update_at TEXT NOT NULL DEFAULT(datetime('now'))
            )
            """
        )

        cursor = conn.execute("PRAGMA table_info(lookout_sources)")
        lookout_source_columns = [row[1] for row in cursor.fetchall()]

        if 'request_method' not in lookout_source_columns:
            conn.execute("ALTER TABLE lookout_sources ADD COLUMN request_method TEXT NOT NULL DEFAULT 'GET'")
        if 'request_headers' not in lookout_source_columns:
            conn.execute("ALTER TABLE lookout_sources ADD COLUMN request_headers TEXT")
        if 'default_params' not in lookout_source_columns:
            conn.execute("ALTER TABLE lookout_sources ADD COLUMN default_params TEXT")
        if 'param_config' not in lookout_source_columns:
            conn.execute("ALTER TABLE lookout_sources ADD COLUMN param_config TEXT")
        if 'extract_rules' not in lookout_source_columns:
            conn.execute("ALTER TABLE lookout_sources ADD COLUMN extract_rules TEXT")
        if 'page_param' not in lookout_source_columns:
            conn.execute("ALTER TABLE lookout_sources ADD COLUMN page_param TEXT NOT NULL DEFAULT 'pn'")
        if 'page_step' not in lookout_source_columns:
            conn.execute("ALTER TABLE lookout_sources ADD COLUMN page_step INTEGER NOT NULL DEFAULT 10")
        if 'keyword_param' not in lookout_source_columns:
            conn.execute("ALTER TABLE lookout_sources ADD COLUMN keyword_param TEXT NOT NULL DEFAULT 'word'")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lookout_records(
                id integer PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                keyword TEXT,
                title TEXT NOT NULL,
                summary TEXT,
                content_url TEXT,
                source_page_url TEXT,
                published_at TEXT,
                raw_payload TEXT,
                content_hash TEXT NOT NULL,
                create_at TEXT NOT NULL DEFAULT(datetime('now')),
                FOREIGN KEY(source_id) REFERENCES lookout_sources(id) ON DELETE CASCADE,
                UNIQUE(source_id, content_hash)
            )
            """
        )

        cursor = conn.execute("PRAGMA table_info(lookout_records)")
        lookout_record_columns = [row[1] for row in cursor.fetchall()]

        if 'keyword' not in lookout_record_columns:
            conn.execute("ALTER TABLE lookout_records ADD COLUMN keyword TEXT")
        if 'source_page_url' not in lookout_record_columns:
            conn.execute("ALTER TABLE lookout_records ADD COLUMN source_page_url TEXT")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lookout_tasks(
                id integer PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER,
                source_name TEXT NOT NULL,
                keyword TEXT,
                page_count INTEGER NOT NULL DEFAULT 1,
                page_size INTEGER NOT NULL DEFAULT 20,
                status TEXT NOT NULL DEFAULT 'pending',
                fetched_count INTEGER NOT NULL DEFAULT 0,
                stored_count INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                create_at TEXT NOT NULL DEFAULT(datetime('now')),
                finish_at TEXT,
                FOREIGN KEY(source_id) REFERENCES lookout_sources(id) ON DELETE SET NULL
            )
            """
        )

        cursor = conn.execute("PRAGMA table_info(lookout_tasks)")
        lookout_task_columns = [row[1] for row in cursor.fetchall()]

        if 'keyword' not in lookout_task_columns:
            conn.execute("ALTER TABLE lookout_tasks ADD COLUMN keyword TEXT")
        if 'page_count' not in lookout_task_columns:
            conn.execute("ALTER TABLE lookout_tasks ADD COLUMN page_count INTEGER NOT NULL DEFAULT 1")
        if 'page_size' not in lookout_task_columns:
            conn.execute("ALTER TABLE lookout_tasks ADD COLUMN page_size INTEGER NOT NULL DEFAULT 20")

        cursor = conn.execute("SELECT COUNT(*) FROM roles")
        if cursor.fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO roles(name, display_name, description, is_system, status) VALUES(?, ?, ?, ?, ?)",
                ("admin", "超级管理员", "系统超级管理员，拥有所有权限", 1, 1)
            )
            conn.execute(
                "INSERT INTO roles(name, display_name, description, is_system, status) VALUES(?, ?, ?, ?, ?)",
                ("user", "普通用户", "普通用户角色，默认权限", 0, 1)
            )

        conn.execute(
            """
            UPDATE roles
            SET display_name = '超级管理员',
                description = '系统超级管理员，拥有所有权限',
                is_system = 1,
                status = 1
            WHERE name = 'admin'
            """
        )

        cursor = conn.execute("SELECT COUNT(*) FROM permissions")
        if cursor.fetchone()[0] == 0:
            conn.execute("INSERT INTO permissions(name, display_name, code, category, parent_id, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                ("首页", "首页", "home", "menu", 0, "fas fa-home", "/admin/", 10))
            conn.execute("INSERT INTO permissions(name, display_name, code, category, parent_id, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                ("系统管理", "系统管理", "system", "group", 0, "fas fa-cog", "", 100))
            system_id = conn.execute("SELECT id FROM permissions WHERE code = 'system'").fetchone()[0]
            conn.execute("INSERT INTO permissions(name, display_name, code, category, parent_id, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                ("用户管理", "用户管理", "user", "menu", system_id, "fas fa-users", "/admin/user", 101))
            conn.execute("INSERT INTO permissions(name, display_name, code, category, parent_id, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                ("角色管理", "角色管理", "role", "menu", system_id, "fas fa-user-shield", "/admin/role", 102))
            conn.execute("INSERT INTO permissions(name, display_name, code, category, parent_id, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                ("功能管理", "功能管理", "permission", "menu", system_id, "fas fa-sitemap", "/admin/permission", 103))
            conn.execute("INSERT INTO permissions(name, display_name, code, category, parent_id, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                ("智能瞭望", "智能瞭望", "lookout", "group", 0, "fas fa-binoculars", "", 200))
            lookout_id = conn.execute("SELECT id FROM permissions WHERE code = 'lookout'").fetchone()[0]
            conn.execute("INSERT INTO permissions(name, display_name, code, category, parent_id, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                ("瞭望源管理", "瞭望源管理", "lookout_source", "menu", lookout_id, "fas fa-globe", "/admin/lookout/source", 201))
            conn.execute("INSERT INTO permissions(name, display_name, code, category, parent_id, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                ("模型管理", "模型管理", "model", "group", 0, "fas fa-brain", "", 300))
            model_id = conn.execute("SELECT id FROM permissions WHERE code = 'model'").fetchone()[0]
            conn.execute("INSERT INTO permissions(name, display_name, code, category, parent_id, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                ("模型配置", "模型配置", "model_config", "menu", model_id, "fas fa-sliders-h", "/admin/model/config", 301))
            conn.execute("INSERT INTO permissions(name, display_name, code, category, parent_id, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                ("数据管理", "数据管理", "data", "group", 0, "fas fa-database", "", 400))
            data_id = conn.execute("SELECT id FROM permissions WHERE code = 'data'").fetchone()[0]
            conn.execute("INSERT INTO permissions(name, display_name, code, category, parent_id, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                ("数据仓库", "数据仓库", "data_warehouse", "menu", data_id, "fas fa-archive", "/admin/data/warehouse", 401))
            conn.execute("INSERT INTO permissions(name, display_name, code, category, parent_id, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                ("系统设置", "系统设置", "settings", "group", 0, "fas fa-tools", "", 500))
            settings_id = conn.execute("SELECT id FROM permissions WHERE code = 'settings'").fetchone()[0]
            conn.execute("INSERT INTO permissions(name, display_name, code, category, parent_id, icon, url, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                ("系统参数", "系统参数", "system_params", "menu", settings_id, "fas fa-cog", "/admin/settings/params", 501))

            conn.execute("INSERT INTO role_permissions(role_id, permission_id) SELECT 1, id FROM permissions")

        conn.execute("UPDATE permissions SET name = '功能管理', display_name = '功能管理', icon = 'fas fa-sitemap' WHERE code = 'permission'")
        conn.execute(
            """
            UPDATE permissions
            SET name = '智能瞭望',
                display_name = '智能瞭望',
                icon = 'fas fa-binoculars',
                sort_order = 200
            WHERE code = 'lookout'
            """
        )

        system_row = conn.execute("SELECT id FROM permissions WHERE code = 'system'").fetchone()
        if system_row:
            conn.execute("UPDATE permissions SET parent_id = ?, category = 'menu' WHERE code IN ('user', 'role', 'permission')", (system_row[0],))

        legacy_robot_row = conn.execute("SELECT id FROM permissions WHERE code = 'robot'").fetchone()
        if legacy_robot_row:
            conn.execute(
                "UPDATE permissions SET parent_id = 0, sort_order = 600, category = 'group' WHERE code = 'robot'"
            )
            conn.execute(
                "UPDATE permissions SET parent_id = ?, sort_order = 601, category = 'menu' WHERE code = 'data_robot'",
                (legacy_robot_row[0],)
            )

        default_permissions = [
            ("首页", "首页", "home", "menu", 0, "fas fa-home", "/admin/", 10),
            ("智能瞭望", "智能瞭望", "lookout", "group", 0, "fas fa-binoculars", "", 200),
            ("模型引擎", "模型引擎", "model", "group", 0, "fas fa-brain", "", 300),
            ("数据管理", "数据管理", "data", "group", 0, "fas fa-database", "", 400),
            ("系统设置", "系统设置", "settings", "group", 0, "fas fa-tools", "", 500),
        ]
        for item in default_permissions:
            conn.execute(
                """INSERT OR IGNORE INTO permissions(name, display_name, code, category, parent_id, icon, url, sort_order)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
                item
            )

        child_permissions = [
            ("lookout", "瞭望源管理", "瞭望源管理", "lookout_source", "menu", "fas fa-globe", "/admin/lookout/source", 201),
            ("lookout", "瞭望采集", "瞭望采集", "lookout_collect", "menu", "fas fa-satellite-dish", "/admin/lookout/collect", 202),
            ("lookout", "采集任务", "采集任务", "lookout_task", "menu", "fas fa-tasks", "/admin/lookout/source#tasks", 203),
            ("model", "模型服务", "模型服务", "model_config", "menu", "fas fa-cubes", "/admin/model", 301),
            ("model", "Token统计", "Token统计", "model_token", "menu", "fas fa-chart-line", "/admin/model#stats", 302),
            ("data", "数据仓库", "数据仓库", "data_warehouse", "menu", "fas fa-archive", "/admin/data/warehouse", 401),
            ("settings", "系统参数", "系统参数", "system_params", "menu", "fas fa-cog", "/admin/settings/params", 501),
        ]
        for parent_code, name, display_name, code, category, icon, url, sort_order in child_permissions:
            parent = conn.execute("SELECT id FROM permissions WHERE code = ?", (parent_code,)).fetchone()
            if parent:
                conn.execute(
                    """INSERT OR IGNORE INTO permissions(name, display_name, code, category, parent_id, icon, url, sort_order)
                       VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
                    (name, display_name, code, category, parent[0], icon, url, sort_order)
                )
                conn.execute(
                    """
                    UPDATE permissions
                    SET name = ?,
                        display_name = ?,
                        category = ?,
                        parent_id = ?,
                        icon = ?,
                        url = ?,
                        sort_order = ?
                    WHERE code = ?
                    """,
                    (name, display_name, category, parent[0], icon, url, sort_order, code)
                )

        conn.execute(
            """
            UPDATE permissions
            SET name = '模型引擎',
                display_name = '模型引擎',
                icon = 'fas fa-brain',
                url = '',
                sort_order = 300,
                category = 'group',
                parent_id = 0
            WHERE code = 'model'
            """
        )
        model_row = conn.execute("SELECT id FROM permissions WHERE code = 'model'").fetchone()
        if model_row:
            conn.execute(
                """
                UPDATE permissions
                SET name = '模型服务',
                    display_name = '模型服务',
                    icon = 'fas fa-cubes',
                    url = '/admin/model',
                    sort_order = 301,
                    parent_id = ?,
                    category = 'menu'
                WHERE code = 'model_config'
                """,
                (model_row[0],)
            )

        conn.execute(
            """
            INSERT OR IGNORE INTO user_roles(user_id, role_id)
            SELECT u.id, r.id
            FROM users u
            INNER JOIN roles r ON r.name = u.role
            WHERE NOT EXISTS (
                SELECT 1 FROM user_roles ur WHERE ur.user_id = u.id
            )
            """
        )

        baidu_target_url = "https://www.baidu.com/s?rtt=1&bsst=1&cl=2&tn=news&rsv_dl=ns_pc&word={keyword}&pn={pn}"
        baidu_headers = """{
  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
  "Accept-Language": "zh-CN,zh;q=0.9",
  "Referer": "https://news.baidu.com/",
  "Upgrade-Insecure-Requests": "1",
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
}"""
        baidu_default_params = """{
  "rtt": "1",
  "bsst": "1",
  "cl": "2",
  "tn": "news",
  "rsv_dl": "ns_pc"
}"""
        baidu_param_config = """[
  {"name": "keyword", "label": "关键字", "required": true, "placeholder": "例如：四川农业大学"},
  {"name": "pn", "label": "分页步进", "required": false, "default": 0, "description": "0=第一页，10=第二页，20=第三页"}
]"""
        baidu_extract_rules = """{
  "engine": "baidu_news_search",
  "link_attr_priority": ["data-landurl", "mu", "href"],
  "summary_window": 420
}"""

        existing_baidu = conn.execute(
            "SELECT id FROM lookout_sources WHERE name = ?",
            ("百度新闻采集",)
        ).fetchone()
        if existing_baidu:
            conn.execute(
                """
                UPDATE lookout_sources
                SET source_type = ?,
                    target_url = ?,
                    request_method = ?,
                    parser_type = ?,
                    request_headers = ?,
                    default_params = ?,
                    param_config = ?,
                    extract_rules = ?,
                    page_param = ?,
                    page_step = ?,
                    keyword_param = ?,
                    status = 1,
                    update_at = datetime('now')
                WHERE id = ?
                """,
                (
                    "search",
                    baidu_target_url,
                    "GET",
                    "baidu_news",
                    baidu_headers,
                    baidu_default_params,
                    baidu_param_config,
                    baidu_extract_rules,
                    "pn",
                    10,
                    "word",
                    existing_baidu[0]
                )
            )
        else:
            conn.execute(
                """
                INSERT INTO lookout_sources(
                    name, source_type, target_url, request_method, parser_type,
                    request_headers, default_params, param_config, extract_rules,
                    page_param, page_step, keyword_param, status, remark
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "百度新闻采集",
                    "search",
                    baidu_target_url,
                    "GET",
                    "baidu_news",
                    baidu_headers,
                    baidu_default_params,
                    baidu_param_config,
                    baidu_extract_rules,
                    "pn",
                    10,
                    "word",
                    1,
                    "预置百度新闻采集模板，可在后台继续调整请求头、参数与提取规则。"
                )
            )
