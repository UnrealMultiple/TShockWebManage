import subprocess
import os
import time
import json


def load_backend_runtime_config(base_dir):
    cfg_path = os.path.join(base_dir, "Server", "server_config.json")
    if not os.path.exists(cfg_path):
        return {}
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("api", {}) if isinstance(data, dict) else {}
    except Exception:
        return {}

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def pick(dct, *keys, default=None):
    for k in keys:
        if isinstance(dct, dict) and k in dct:
            return dct[k]
    return default


def normalize_port(port_value):
    if port_value is None:
        return None
    try:
        p = int(port_value)
    except (TypeError, ValueError):
        return None
    if 1 <= p <= 65535:
        return p
    return None


def build_cmd(name, settings, backend_runtime_cfg=None):
    cmd = str(pick(settings, "命令", "cmd", default="")).strip()
    host = str(pick(settings, "主机", "host", default="")).strip()
    port = normalize_port(pick(settings, "端口", "port", default=None))

    # 支持在命令中显式写占位符
    if "{主机}" in cmd:
        cmd = cmd.replace("{主机}", host)
    if "{host}" in cmd:
        cmd = cmd.replace("{host}", host)
    if port is not None:
        if "{端口}" in cmd:
            cmd = cmd.replace("{端口}", str(port))
        if "{port}" in cmd:
            cmd = cmd.replace("{port}", str(port))

    # 后端服务默认追加 host/port（若命令里未写）
    is_server = any(x in str(name) for x in ("server", "后端", "api"))
    if is_server:
        if not host:
            host = str((backend_runtime_cfg or {}).get("host", "")).strip()
        if port is None:
            port = normalize_port((backend_runtime_cfg or {}).get("port"))

    host = host or "127.0.0.1"

    if is_server and "uvicorn" in cmd.lower():
        if "--host" not in cmd:
            cmd += f" --host {host}"
        if port is not None and "--port" not in cmd:
            cmd += f" --port {port}"

    return cmd

def run():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config = load_config()
    backend_runtime_cfg = load_backend_runtime_config(base_dir)

    for name, settings in config.items():
        print(f"正在启动 {name}...")

        # 转换绝对路径
        path = pick(settings, "路径", "path", default="")
        if not path:
            print(f"[跳过] {name} 未配置 路径/path")
            continue

        work_dir = os.path.join(base_dir, path)
        cmd = build_cmd(name, settings, backend_runtime_cfg)
        if not cmd:
            print(f"[跳过] {name} 未配置 命令/cmd")
            continue

        # 启动独立控制台窗口
        subprocess.Popen(
            f"cmd /c {cmd}",
            cwd=work_dir,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

        # 处理启动间隔
        delay = pick(settings, "延时", "delay", default=None)
        if delay is not None:
            try:
                time.sleep(float(delay))
            except (TypeError, ValueError):
                pass

if __name__ == "__main__":
    run()