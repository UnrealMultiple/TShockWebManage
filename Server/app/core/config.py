import os
import json
import sys
import secrets

# ── 配置加载 ──────────────────────────────────────────────────
# __file__ 是 app/core/config.py，需要向上三层到达 Server/ 根目录。
# 打包为 exe 时以可执行文件所在目录作为基准目录。
if getattr(sys, "frozen", False):
    _base_dir = os.path.dirname(os.path.abspath(sys.executable))
else:
    _base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_base_dir, "server_config.json")


def _generate_jwt_secret() -> str:
    """生成安全的随机 JWT 密钥"""
    return secrets.token_hex(32)  # 64 位十六进制字符串


def _generate_bootstrap_token() -> str:
    """生成一次性平台初始化令牌"""
    return secrets.token_urlsafe(24)


def _default_config() -> dict:
    return {
        "接口": {
            "主机": "127.0.0.1",
            "端口": 8000,
        },
        "邮件服务": {
            "主机": "smtp.qq.com",
            "端口": 587,
            "用户": "",
            "授权码": "",
            "发件人名称": "TShock 管理平台",
        },
        "JWT 密钥": _generate_jwt_secret(),  # 自动生成随机密钥
        "平台初始化令牌": _generate_bootstrap_token(),
    }


def _load_or_create_config(path: str) -> dict:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        changed = False
        # 兼容旧配置：如果没有 JWT 密钥，自动生成
        if "JWT 密钥" not in cfg or not cfg.get("JWT 密钥"):
            cfg["JWT 密钥"] = _generate_jwt_secret()
            changed = True
        if "平台初始化令牌" not in cfg or not cfg.get("平台初始化令牌"):
            cfg["平台初始化令牌"] = _generate_bootstrap_token()
            changed = True
        if changed:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=4)
            except Exception:
                pass
        return cfg

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
SMTP_HOST      = _cfg.get("邮件服务", {}).get("主机", "smtp.qq.com")
SMTP_PORT      = int(_cfg.get("邮件服务", {}).get("端口", 587))
SMTP_USER      = _cfg.get("邮件服务", {}).get("用户", "")
SMTP_PASS      = _cfg.get("邮件服务", {}).get("授权码", "")
SMTP_FROM_NAME = _cfg.get("邮件服务", {}).get("发件人名称", "TShock 管理平台")

# API 监听配置
API_HOST       = _cfg.get("接口", {}).get("主机", "127.0.0.1")
API_PORT       = int(_cfg.get("接口", {}).get("端口", 8000))

# 安全配置
JWT_SECRET     = _cfg.get("JWT 密钥", "dev-secret")
JWT_HOURS      = 24

# 初始平台管理员配置（保留兼容，已不再作为主流程）
INITIAL_PLATFORM_ADMIN = _cfg.get("初始平台管理员", "")
BOOTSTRAP_TOKEN = _cfg.get("平台初始化令牌", "")

# 数据库路径
AUTH_DB_PATH   = os.path.join(_base_dir, "auth.sqlite")
