import argparse

import uvicorn

from app.main import app
from app.core.config import API_HOST, API_PORT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TShock 管理平台后端")
    parser.add_argument("--host", default=API_HOST, help="监听地址")
    parser.add_argument("--port", type=int, default=API_PORT, help="监听端口")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    uvicorn.run(app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
