"""
插件文档：返回前端应尝试的所有镜像 URL 列表，由浏览器并发竞速获取。
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/plugin", tags=["Plugins"])

# 按成功率排序的镜像模板（{name} 待前端替换）
README_MIRRORS = [
    "https://cdn.jsdelivr.net/gh/UnrealMultiple/TShockPlugin@master/src/{name}/README.md",
    "https://raw.gitmirror.com/UnrealMultiple/TShockPlugin/master/src/{name}/README.md",
    "https://ghfast.top/https://raw.githubusercontent.com/UnrealMultiple/TShockPlugin/master/src/{name}/README.md",
    "https://gh.llkk.cc/https://raw.githubusercontent.com/UnrealMultiple/TShockPlugin/master/src/{name}/README.md",
    "https://raw.githubusercontent.com/UnrealMultiple/TShockPlugin/master/src/{name}/README.md",
]

@router.get("/mirrors")
def get_mirrors():
    """返回前端应尝试的镜像 URL 列表"""
    return JSONResponse({"mirrors": README_MIRRORS})
