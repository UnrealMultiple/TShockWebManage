from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

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

class BootstrapPlatformAdminReq(BaseModel):
    bootstrap_token: str

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
    join_requires_approval: bool = False
    game_ip:      Optional[str]  = Field("",         max_length=100)
    game_port:    Optional[int]  = None
    qq_group:     Optional[str]  = Field("",         max_length=20)
    game_version: Optional[str]  = Field("",         max_length=50)
    show_ip:      bool = True

class ServerJoinReq(BaseModel):
    """提交入服申请：使用服务器编号"""
    server_code: str = Field(..., min_length=6, max_length=32)

class ServerUpdateReq(BaseModel):
    """更新服务器基本信息（Owner 专属）"""
    name:         Optional[str]  = Field(None, max_length=50)
    description:  Optional[str]  = Field(None, max_length=200)
    is_public:    Optional[bool] = None
    join_requires_approval: Optional[bool] = None
    game_ip:      Optional[str]  = Field(None, max_length=100)
    game_port:    Optional[int]  = None
    qq_group:     Optional[str]  = Field(None, max_length=20)
    game_version: Optional[str]  = Field(None, max_length=50)
    show_ip:      Optional[bool] = None

class ServerMemberOut(BaseModel):
    user_id:        int
    email:          str
    role:           str
    joined_at:      int
    panel_group_id:   Optional[int] = None
    panel_group_name: Optional[str] = None

class ServerOut(BaseModel):
    id:          int
    server_code: str
    name:        str
    description: str
    agent_key:   str
    owner_id:    Optional[int]
    created_at:  int
    is_public:   bool = False
    join_requires_approval: bool = False
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
    register_limit: int = 1
    blacklist_auto_reject_count: int = 0
    character_name_regex: str = r"^[\u4e00-\u9fffA-Za-z0-9:/\[\]]+$"
    character_name_max_length: int = 20
    # 平台侧审核/展示状态
    platform_status: str = "active"
    platform_audit_status: str = "pending"
    platform_audit_reason: Optional[str] = None
    platform_is_public: bool = False

class ServerDetailOut(ServerOut):
    members: List[ServerMemberOut] = []

class UpdateMemberRoleReq(BaseModel):
    """更新成员面板角色"""
    role: str  # 服主 / 网页管理员 / 成员

class BindVerifyReq(BaseModel):
    """绑定已有游戏角色的验证码校验"""
    username: str
    code: str

class AssignCharacterOwnerReq(BaseModel):
    """管理员手动分配或修改游戏账号归属"""
    character_name: str
    target_user_id: Optional[int] = None


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


# ── 面板功能管理相关模型 ─────────────────────────────────────────────────

class PanelFeatureSettingsUpdate(BaseModel):
    register_limit: int = Field(..., ge=0, le=50)
    blacklist_auto_reject_count: int = Field(0, ge=0, le=99)
    character_name_regex: str = Field(r"^[\u4e00-\u9fffA-Za-z0-9:/\[\]]+$", min_length=1, max_length=256)
    character_name_max_length: int = Field(20, ge=1, le=50)


class PanelFeatureSettingsOut(BaseModel):
    register_limit: int = Field(default=1, ge=0, le=50)
    registered_count: int = 0
    join_requires_approval: bool = False
    blacklist_auto_reject_count: int = 0
    character_name_regex: str = r"^[\u4e00-\u9fffA-Za-z0-9:/\[\]]+$"
    character_name_max_length: int = 20
    server_code: str = ""


class PanelMembershipInviteReq(BaseModel):
    invitee_email: str = Field(..., max_length=128)
    message: Optional[str] = Field("", max_length=300)
    expires_in_hours: Optional[int] = Field(72, ge=1, le=720)


class PanelMembershipReviewReq(BaseModel):
    note: Optional[str] = Field("", max_length=300)


class BlacklistCreateReq(BaseModel):
    target_user_id: int
    reason: Optional[str] = Field("", max_length=500)


class CloudBlacklistReviewReq(BaseModel):
    action: str = Field(..., max_length=16)
    review_note: Optional[str] = Field("", max_length=500)


# ── 消息中心 / 邀请 / 申请相关模型 ───────────────────────────────────────────────

class ServerApplyReq(BaseModel):
    message: Optional[str] = Field("", max_length=300)


class JoinRequestReviewReq(BaseModel):
    note: Optional[str] = Field("", max_length=300)


class JoinRequestOut(BaseModel):
    id: int
    server_id: int
    server_name: str = ""
    server_code: str = ""
    applicant_user_id: int
    applicant_email: str
    message: str = ""
    status: str
    reviewed_by_user_id: Optional[int] = None
    reviewed_by_email: Optional[str] = None
    review_note: str = ""
    created_at: int
    updated_at: int
    withdrawn_at: Optional[int] = None
    server_blacklist_count: int = 0
    cloud_blacklist_count: int = 0
    blacklist_flags: List[str] = []
    blacklist_details: List[Dict[str, Any]] = []


class ServerInviteCreateReq(BaseModel):
    invitee_email: str = Field(..., max_length=128)
    message: Optional[str] = Field("", max_length=300)
    expires_in_hours: Optional[int] = Field(72, ge=1, le=720)


class ServerInviteRespondReq(BaseModel):
    action: str = Field(..., max_length=16)
    note: Optional[str] = Field("", max_length=300)


class ServerInviteOut(BaseModel):
    id: int
    server_id: int
    server_name: str = ""
    server_code: str = ""
    inviter_user_id: int
    inviter_email: Optional[str] = None
    invitee_user_id: int
    invitee_email: Optional[str] = None
    message: str = ""
    status: str
    expires_at: Optional[int] = None
    acted_at: Optional[int] = None
    created_at: int
    updated_at: int


class NotificationOut(BaseModel):
    id: int
    receiver_user_id: int
    sender_user_id: Optional[int] = None
    sender_email: Optional[str] = None
    server_id: Optional[int] = None
    server_name: Optional[str] = None
    type: str
    ref_type: Optional[str] = None
    ref_id: Optional[int] = None
    title: str
    content: str
    payload_json: str = "{}"
    created_at: int
    read_at: Optional[int] = None


class UserOut(BaseModel):
    """平台用户输出模型"""
    id: int
    email: str
    username: Optional[str] = None
    is_platform_admin: bool = False
