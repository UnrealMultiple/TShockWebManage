# 项目接口与协议文档 (protocol)

更新时间: 2026-03-16
适用后端: FastAPI + WebSocket

## 1. 总览

本项目包含两类通信接口:

1. HTTP REST 接口: 账号、服务器管理、RBAC、数据库浏览、插件镜像列表。
2. WebSocket 协议: Web 端实时操作链路与 Agent 执行链路。

## 2. 通用约定

### 2.1 HTTP 基础

1. Base URL 示例: `http://127.0.0.1:7773`
2. JSON 编码: `application/json`
3. 认证方式: `Authorization: Bearer <token>`
4. 错误返回: FastAPI 标准 `{"detail": "错误信息"}`

### 2.2 WebSocket 信封格式

所有 WS 消息统一采用如下信封:

```json
{
  "type": "消息类型",
  "msg_id": "唯一消息ID",
  "timestamp": 1710000000000,
  "payload": {},
  "metadata": {}
}
```

字段说明:

1. `type`: 消息类型。
2. `msg_id`: 请求唯一标识，回执通过 `ref_id` 关联。
3. `timestamp`: 毫秒时间戳。
4. `payload`: 业务数据。
5. `metadata`: 可选，服务端可能注入 `agent_key` 等路由信息。

## 3. HTTP 接口

## 3.1 认证接口 `/api/auth`

### 3.1.1 发送注册验证码

- 方法: `POST`
- 路径: `/api/auth/send-code`
- 鉴权: 否
- 请求体:

```json
{
  "email": "user@example.com",
  "password": "123456"
}
```

- 响应:

```json
{"ok": true}
```

### 3.1.2 注册

- 方法: `POST`
- 路径: `/api/auth/register`
- 鉴权: 否
- 请求体:

```json
{
  "email": "user@example.com",
  "password": "123456",
  "code": "123456"
}
```

- 响应:

```json
{"ok": true, "token": "...", "email": "user@example.com"}
```

### 3.1.3 登录

- 方法: `POST`
- 路径: `/api/auth/login`
- 鉴权: 否
- 请求体:

```json
{
  "email": "user@example.com",
  "password": "123456"
}
```

- 响应:

```json
{"ok": true, "token": "...", "email": "user@example.com"}
```

### 3.1.4 忘记密码-发送验证码

- 方法: `POST`
- 路径: `/api/auth/reset-send-code`
- 鉴权: 否
- 请求体:

```json
{"email": "user@example.com"}
```

- 响应:

```json
{"ok": true}
```

### 3.1.5 忘记密码-确认重置

- 方法: `POST`
- 路径: `/api/auth/reset-confirm`
- 鉴权: 否
- 请求体:

```json
{
  "email": "user@example.com",
  "code": "123456",
  "new_password": "newpass"
}
```

- 响应:

```json
{"ok": true}
```

## 3.2 服务器接口 `/api/servers`

### 3.2.1 认领服务器

- `POST /api/servers/claim`
- 鉴权: 是
- 请求体关键字段:

```json
{
  "agent_key": "agent-xxx",
  "name": "我的服务器",
  "description": "说明",
  "is_public": false,
  "game_ip": "",
  "game_port": null,
  "qq_group": "",
  "game_version": "",
  "show_ip": true
}
```

### 3.2.2 加入服务器

- `POST /api/servers/join`
- 鉴权: 是
- 请求体: `{"server_id": 1}`

### 3.2.3 列出我参与的服务器

- `GET /api/servers`
- 鉴权: 是

### 3.2.4 列出公开服务器

- `GET /api/servers/public`
- 鉴权: 是

### 3.2.5 获取服务器详情

- `GET /api/servers/{server_id}`
- 鉴权: 是

### 3.2.6 离开服务器

- `DELETE /api/servers/{server_id}/leave`
- 鉴权: 是

### 3.2.7 踢出成员

- `DELETE /api/servers/{server_id}/members/{target_user_id}`
- 鉴权: 是 (Owner)

### 3.2.8 解散服务器

- `DELETE /api/servers/{server_id}`
- 鉴权: 是 (Owner)

### 3.2.9 更新服务器信息

- `PATCH /api/servers/{server_id}`
- 鉴权: 是 (Owner)

### 3.2.10 修改成员角色

- `PATCH /api/servers/{server_id}/members/{target_user_id}/role`
- 鉴权: 是 (Owner)
- 请求体: `{"role": "owner|web_staff|member"}`

### 3.2.11 成员角色/绑定相关

1. `GET /api/servers/{server_id}/members/{target_user_id}/characters`
2. `GET /api/servers/{server_id}/my-characters`
3. `DELETE /api/servers/{server_id}/my-characters/{character_name}`
4. `DELETE /api/servers/{server_id}/members/{target_user_id}/characters/{character_name}`
5. `POST /api/servers/{server_id}/bind-verify`
6. `GET /api/servers/{server_id}/character-map`

`bind-verify` 请求体:

```json
{
  "username": "角色名",
  "code": "123456"
}
```

## 3.3 面板权限组接口 (归属 `/api/servers`)

1. `GET /api/servers/{server_id}/panel-groups`
2. `POST /api/servers/{server_id}/panel-groups`
3. `PUT /api/servers/{server_id}/panel-groups/{group_id}`
4. `DELETE /api/servers/{server_id}/panel-groups/{group_id}`
5. `PUT /api/servers/{server_id}/members/{target_user_id}/panel-group`
6. `GET /api/servers/{server_id}/members/{target_user_id}/panel-group`

创建权限组请求体示例:

```json
{
  "name": "管理",
  "description": "描述",
  "permissions": ["panel.console", "panel.files"]
}
```

## 3.4 RBAC 接口 `/api/rbac`

1. `GET /api/rbac/groups`
2. `POST /api/rbac/groups`
3. `DELETE /api/rbac/groups/{group_id}`
4. `POST /api/rbac/users/{email}/groups`
5. `GET /api/rbac/users`

鉴权: 是 (`rbac.manage` 权限)

用户组更新请求体:

```json
{
  "groups": ["admin", "default"]
}
```

## 3.5 数据库接口 `/api/db`

1. `GET /api/db/list`
2. `GET /api/db/{db_name}/tables`
3. `GET /api/db/{db_name}/table/{table_name}?page=1&page_size=50`
4. `PUT /api/db/{db_name}/table/{table_name}/row`
5. `POST /api/db/{db_name}/table/{table_name}/row`
6. `DELETE /api/db/{db_name}/table/{table_name}/row`

说明:

1. `db_name` 白名单: `auth`, `tshock`
2. 对 `auth` 写操作需要超级管理员权限 (`*`)
3. 表名/列名做了标识符校验，防止注入

更新行请求体示例:

```json
{
  "pk_col": "id",
  "pk_val": 1,
  "data": {
    "name": "new-name"
  }
}
```

## 3.6 插件镜像接口 `/api/plugin`

1. `GET /api/plugin/mirrors`

响应示例:

```json
{
  "mirrors": [
    "https://cdn.jsdelivr.net/gh/.../src/{name}/README.md",
    "https://raw.githubusercontent.com/.../src/{name}/README.md"
  ]
}
```

## 4. WebSocket 接口

## 4.1 Web 端连接入口

1. 路径: `/ws/web`
2. 鉴权参数: `token` (query)
3. 失败行为: 返回 `{"type":"error","msg":"未授权"}` 后关闭 (code=4001)

连接成功后服务端返回 `auth` 消息，`payload` 包含:

1. `client_id`
2. `role`: `web`
3. `email`
4. `online_agents`: 当前用户可见在线 Agent 列表

## 4.2 Agent 连接入口

1. 路径: `/ws/agent`
2. 必需参数: `agent_key` (query)
3. 未传 `agent_key`: 关闭连接 (code=4003)
4. 同 key 重连: 旧连接会被踢下线

连接成功后返回 `auth`，并向成员广播 `agent_status` 上线消息。

## 4.3 Web -> Server 消息类型

## 4.3.1 控制台与服务器控制

1. `cmd`
2. `server_ctrl`
3. `local_server_start`
4. `local_force_kill`

共同规则:

1. 必须包含 `payload.agent_key`
2. 执行权限: `has_console_access`
3. 目标 Agent 离线会返回 `*_resp` 失败

## 4.3.2 角色与玩家相关

1. `register_user`
2. `send_bind_code`
3. `get_char_info`
4. `player_list`
5. `player_action`
6. `world_progress`
7. `player_stats`

权限规则简述:

1. `player_list/player_action`: 需要控制台权限
2. `world_progress/player_stats`: 服务器成员可用

## 4.3.3 文件/数据库/配置/插件/背包类

可发送类型 (会转发给 Agent，并期待 `*_resp`):

1. `file_list`
2. `file_read`, `file_write`, `file_delete`
3. `db_query`, `db_exec`, `db_update_row`, `db_delete_row`, `db_insert_row`
4. `read_tshock_config`, `write_tshock_config`, `reload_tshock`
5. `read_startup_script`, `write_startup_script`
6. `read_motd`, `write_motd`
7. `plugin_list_configs`, `plugin_cloud_list`
8. `plugin_check_apm`, `plugin_install_apm`
9. `plugin_local_list`, `plugin_install`, `plugin_uninstall`
10. `plugin_check_updates`, `plugin_update`
11. `plugin_disable`, `plugin_enable`, `plugin_blacklist`
12. `get_minimap`, `get_player_positions`
13. `get_inventory`, `save_inventory`, `get_groups`

备注:

1. `get_inventory` 支持细粒度权限: `panel.inventory.view.self` / `panel.inventory.view.others`
2. `save_inventory` 仅高权限可用

## 4.4 Agent -> Server 消息类型

1. `status`
2. `register_user_resp`
3. `get_char_info_resp`
4. `send_bind_code_resp`
5. `world_progress_resp`
6. `player_stats_resp`
7. `read_startup_script_resp`
8. 通用业务回执与日志类 (见 4.5)

服务端处理策略:

1. `status`: 更新 game_version 并向成员广播
2. `register_user_resp`: 成功时写入角色绑定，再广播
3. `read_startup_script_resp`: 自动探测时会回写 `local_start_path`

## 4.5 Server -> Web 广播消息类型

常见下行类型:

1. `agent_status`
2. `status`
3. `log`, `chat`
4. `cmd_resp`, `server_ctrl_resp`
5. `file_list_resp`, `file_read_resp`, `file_write_resp`, `file_delete_resp`
6. `db_query_resp`, `db_exec_resp`, `db_update_row_resp`, `db_delete_row_resp`, `db_insert_row_resp`
7. `player_list_resp`, `player_action_resp`
8. `read_tshock_config_resp`, `write_tshock_config_resp`, `reload_tshock_resp`
9. `read_startup_script_resp`, `write_startup_script_resp`
10. `read_motd_resp`, `write_motd_resp`
11. `plugin_*_resp`
12. `minimap_resp`, `player_positions_resp`
13. `get_inventory_resp`, `save_inventory_resp`, `get_groups_resp`

路由策略:

1. 成员广播: `broadcast_agent_to_members`
2. 管理权限广播: `broadcast_agent_to_authorized_webs`
3. 服务端会在 `metadata.agent_key` 注入来源服务器标识

## 5. 典型消息示例

## 5.1 Web 下发命令

```json
{
  "type": "cmd",
  "msg_id": "m-1001",
  "timestamp": 1710000000000,
  "payload": {
    "agent_key": "agent-001",
    "raw_cmd": "/kick Alice"
  }
}
```

## 5.2 回执消息

```json
{
  "type": "cmd_resp",
  "msg_id": "r-2001",
  "timestamp": 1710000000100,
  "payload": {
    "ref_id": "m-1001",
    "success": true,
    "output": "执行成功"
  },
  "metadata": {
    "agent_key": "agent-001"
  }
}
```

## 6. 错误码与常见失败

## 6.1 HTTP

1. `400`: 参数错误/验证码错误/非法标识符
2. `401`: 未登录或 Token 无效
3. `403`: 权限不足
4. `404`: 资源不存在
5. `409`: 冲突 (如重复认领、重复加入)

## 6.2 WebSocket

1. `4001`: Web 端未授权
2. `4003`: Agent 缺少 `agent_key`
3. 业务失败通常通过 `*_resp.payload.success=false` + `msg/output` 返回

## 7. 兼容与扩展建议

1. 新增 WS 类型时，保持 `msg_id/ref_id` 关联机制不变。
2. 新增 HTTP 接口时，统一 Bearer 鉴权与错误格式。
3. 建议在前端按 `type` + `ref_id` 做回执分发，避免并发请求串包。
4. 生产环境建议启用 HTTPS/WSS，避免混合内容问题。
