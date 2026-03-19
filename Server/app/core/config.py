import os
import json
import sys

# ── 配置加载 ──────────────────────────────────────────────────
# __file__ 是 app/core/config.py，需要向上三层到达 Server/ 根目录。
# 打包为 exe 时以可执行文件所在目录作为基准目录。
if getattr(sys, "frozen", False):
    _base_dir = os.path.dirname(os.path.abspath(sys.executable))
else:
    _base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_base_dir, "server_config.json")


def _default_config() -> dict:
    return {
        "api": {
            "host": "127.0.0.1",
            "port": 8000,
        },
        "smtp": {
            "host": "smtp.qq.com",
            "port": 587,
            "user": "",
            "auth_code": "",
            "from_name": "TShock 管理平台",
        },
        "jwt_secret": "dev-secret-please-change",
    }


def _load_or_create_config(path: str) -> dict:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    cfg = _default_config()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
    except Exception:
        # 只影响首次落盘，不阻断服务启动。
        pass
    return cfg


_cfg: dict = _load_or_create_config(_CONFIG_PATH)

# SMTP 配置
SMTP_HOST      = _cfg.get("smtp", {}).get("host", "smtp.qq.com")
SMTP_PORT      = int(_cfg.get("smtp", {}).get("port", 587))
SMTP_USER      = _cfg.get("smtp", {}).get("user", "")
SMTP_PASS      = _cfg.get("smtp", {}).get("auth_code", "")
SMTP_FROM_NAME = _cfg.get("smtp", {}).get("from_name", "TShock 管理平台")

# API 监听配置
API_HOST       = _cfg.get("api", {}).get("host", "127.0.0.1")
API_PORT       = int(_cfg.get("api", {}).get("port", 8000))

# 安全配置
JWT_SECRET     = _cfg.get("jwt_secret", "dev-secret-please-change")
JWT_HOURS      = 24

# 数据库路径
AUTH_DB_PATH   = os.path.join(_base_dir, "auth.sqlite")
TS_DB_PATH     = os.path.join(_base_dir, "..", "Agent", "bin", "TShock", "tshock", "tshock.sqlite")
