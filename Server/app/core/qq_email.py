import re

from fastapi import HTTPException


QQ_NUMBER_RE = re.compile(r"^[1-9]\d{4,11}$")


def normalize_qq_email(value: str, message: str = "请输入正确的 QQ 号或 QQ 邮箱") -> str:
    raw = str(value or "").strip().lower()
    if raw.endswith("@qq.com"):
        qq = raw[:-7]
    elif "@" in raw:
        raise HTTPException(400, message)
    else:
        qq = raw

    if not QQ_NUMBER_RE.fullmatch(qq):
        raise HTTPException(400, message)
    return f"{qq}@qq.com"
