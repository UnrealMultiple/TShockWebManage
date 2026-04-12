from pydantic import BaseModel, Field
from typing import List, Optional

class SendCodeReq(BaseModel):
    email: str
    password: str

class RegisterReq(BaseModel):
    email: str
    password: str
    code: str

class LoginReq(BaseModel):
    email: str
    password: str

class ResetSendCodeReq(BaseModel):
    email: str

class ResetConfirmReq(BaseModel):
    email: str
    code: str
    new_password: str

# RBAC 相关模型
class GroupBase(BaseModel):
    name: str
    parent_id: Optional[int] = None
    description: Optional[str] = None

class GroupCreate(GroupBase):
    permissions: List[str] = []

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class UserGroupUpdate(BaseModel):
    groups: List[str] # 组名列表


# ── 服务器管理相关模型 ───────────────────────────────────────────

class ServerClaimReq(BaseModel):
    """认领服务器：用户凭 agent_key 成为 Owner"""
    agent_key:    str             = Field(...,        max_length=100)
    name:         str             = Field(...,        max_length=50)
    description:  Optional[str]  = Field("",         max_length=200)
    is_public:    bool = False
    game_ip:      Optional[str]  = Field("",         max_length=100)
    game_port:    Optional[int]  = None
    qq_group:     Optional[str]  = Field("",         max_length=20)
    game_version: Optional[str]  = Field("",         max_length=50)
    show_ip:      bool = True

class ServerJoinReq(BaseModel):
    """加入服务器：成为普通 Member"""
    server_id: int

class ServerUpdateReq(BaseModel):
    """更新服务器基本信息（Owner 专属）"""
    name:         Optional[str]  = Field(None, max_length=50)
    description:  Optional[str]  = Field(None, max_length=200)
    is_public:    Optional[bool] = None
    game_ip:      Optional[str]  = Field(None, max_length=100)
    game_port:    Optional[int]  = None
    qq_group:     Optional[str]  = Field(None, max_length=20)
    game_version: Optional[str]  = Field(None, max_length=50)
    show_ip:      Optional[bool] = None
    local_start_enabled: Optional[bool] = None
    local_start_path:    Optional[str]  = Field(None, max_length=512)

class ServerMemberOut(BaseModel):
    user_id:        int
    email:          str
    role:           str
    joined_at:      int
    panel_group_id:   Optional[int] = None
    panel_group_name: Optional[str] = None

class ServerOut(BaseModel):
    id:          int
    name:        str
    description: str
    agent_key:   str
    owner_id:    Optional[int]
    created_at:  int
    is_public:   bool = False
    online:      bool = False          # 代理端是否在线（由 WebSocket 层填充）
    member_count: int = 0
    server_role: Optional[str] = None  # 当前登录用户在该服务器的角色
    panel_group_name: Optional[str] = None        # 当前用户所在面板权限组名
    panel_permissions: Optional[List[str]] = None  # 面板权限组拥有的权限列表
    # 游戏连接信息
    game_ip:      Optional[str] = ""
    game_port:    Optional[int] = None
    qq_group:     Optional[str] = ""
    game_version: Optional[str] = ""
    show_ip:      bool = True
    # 同机直接启动配置
    local_start_enabled: bool = False
    local_start_path:    str  = ""

class ServerDetailOut(ServerOut):
    members: List[ServerMemberOut] = []

class UpdateMemberRoleReq(BaseModel):
    """更新成员面板角色"""
    role: str  # 服主 / 网页管理员 / 成员

class BindVerifyReq(BaseModel):
    """绑定已有游戏角色的验证码校验"""
    username: str
    code: str


# ── 面板权限组相关模型 ──────────────────────────────────────────────────────

class PanelGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parent_group_id: Optional[int] = None
    permissions: List[str] = []

class PanelGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_group_id: Optional[int] = None
    permissions: Optional[List[str]] = None

class PanelGroupOut(BaseModel):
    id: int
    server_id: int
    name: str
    description: Optional[str] = None
    parent_group_id: Optional[int] = None
    parent_group_name: Optional[str] = None
    is_builtin: bool
    permissions: List[str]
    effective_permissions: List[str] = []
    member_count: int = 0

class PanelMemberGroupUpdate(BaseModel):
    group_id: int
