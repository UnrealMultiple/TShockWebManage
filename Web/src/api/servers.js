import { getToken } from '@/api/auth'
import { apiUrl } from '@/api/base'

function authHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getToken()}`,
  }
}

async function request(method, path, body) {
  const options = { method, headers: authHeaders() }
  if (body !== undefined) options.body = JSON.stringify(body)
  const res = await fetch(apiUrl(path), options)
  let data
  try {
    data = await res.json()
  } catch {
    throw new Error(`服务器错误 (${res.status})`)
  }
  if (!res.ok) throw new Error(data.detail || '请求失败')
  return data
}

/** 认领服务器 */
export function claimServer(agent_key, name, description = '', is_public = false, extra = {}) {
  return request('POST', '/api/servers/claim', {
    agent_key, name, description, is_public,
    join_requires_approval: extra.join_requires_approval ?? false,
    game_ip:   extra.game_ip   ?? '',
    game_port: extra.game_port ?? null,
    qq_group:  extra.qq_group  ?? '',
    show_ip:   extra.show_ip   ?? true,
  })
}

/** 按服务器编号申请加入 */
export function applyJoinServerByCode(server_code) {
  return request('POST', '/api/servers/apply', { server_code })
}

/** 在已知服务器上下文中提交申请 */
export function applyJoinServer(server_id, message = '') {
  return request('POST', `/api/servers/${server_id}/apply`, { message })
}

/** 撤回入服申请 */
export function withdrawJoinRequest(server_id, request_id) {
  return request('POST', `/api/servers/${server_id}/join-requests/${request_id}/withdraw`)
}

/** 服主查看入服申请 */
export function listJoinRequests(server_id, status) {
  const q = new URLSearchParams()
  if (status) q.set('status', status)
  const suffix = q.toString() ? `?${q.toString()}` : ''
  return request('GET', `/api/servers/${server_id}/join-requests${suffix}`)
}

/** 服主批准入服申请 */
export function approveJoinRequest(server_id, request_id, note = '') {
  return request('POST', `/api/servers/${server_id}/join-requests/${request_id}/approve`, { note })
}

/** 服主拒绝入服申请 */
export function rejectJoinRequest(server_id, request_id, note = '') {
  return request('POST', `/api/servers/${server_id}/join-requests/${request_id}/reject`, { note })
}

/** 服主发邀请 */
export function createServerInvite(server_id, invitee_email, message = '', expires_in_hours = 72) {
  return request('POST', `/api/servers/${server_id}/invites`, {
    invitee_email,
    message,
    expires_in_hours,
  })
}

/** 服主查看邀请记录 */
export function listServerInvites(server_id, status) {
  const q = new URLSearchParams()
  if (status) q.set('status', status)
  const suffix = q.toString() ? `?${q.toString()}` : ''
  return request('GET', `/api/servers/${server_id}/invites${suffix}`)
}

/** 获取当前用户参与的所有服务器 */
export function listServers() {
  return request('GET', '/api/servers')
}

/** 获取所有公开的服务器 */
export function listPublicServers() {
  return request('GET', '/api/servers/public')
}

/** 获取服务器详情（含成员列表） */
export function getServer(server_id) {
  return request('GET', `/api/servers/${server_id}`)
}

/** 离开服务器 */
export function leaveServer(server_id) {
  return request('DELETE', `/api/servers/${server_id}/leave`)
}

/** 踢出成员（服主） */
export function kickMember(server_id, user_id) {
  return request('DELETE', `/api/servers/${server_id}/members/${user_id}`)
}

/** 解散服务器（服主） */
export function dissolveServer(server_id) {
  return request('DELETE', `/api/servers/${server_id}`)
}

/** 更新服务器信息（服主） */
export function updateServer(server_id, data) {
  return request('PATCH', `/api/servers/${server_id}`, data)
}

/** 玩家删除自己的游戏角色绑定 */
export function deleteMyCharacter(server_id, character_name) {
  return request('DELETE', `/api/servers/${server_id}/my-characters/${encodeURIComponent(character_name)}`)
}

/** 服主/管理员删除指定成员的游戏角色 */
export function deleteMemberCharacter(server_id, target_user_id, character_name) {
  return request('DELETE', `/api/servers/${server_id}/members/${target_user_id}/characters/${encodeURIComponent(character_name)}`)
}

/** 手动分配或修改游戏账号归属（服主/网页管理员） */
export function assignCharacterOwner(server_id, { character_name, target_user_id }) {
  return request('POST', `/api/servers/${server_id}/characters/assign`, { character_name, target_user_id })
}

/** 兼容旧调用名 */
export function assignUnboundCharacter(server_id, payload) {
  return assignCharacterOwner(server_id, payload)
}

/** 删除游戏账号（删除绑定并请求 Agent 删除 TShock 账号） */
export function deleteGameAccount(server_id, character_name) {
  return request('DELETE', `/api/servers/${server_id}/characters?character_name=${encodeURIComponent(character_name)}`)
}
// ── 面板权限组 ───────────────────────────────────────────────────────────────

/** 列出服务器所有面板权限组 */
export function listPanelGroups(server_id) {
  return request('GET', `/api/servers/${server_id}/panel-groups`)
}

/** 创建面板权限组（服主） */
export function createPanelGroup(server_id, { name, description, parent_group_id, permissions }) {
  return request('POST', `/api/servers/${server_id}/panel-groups`, { name, description, parent_group_id, permissions })
}

/** 更新面板权限组（服主） */
export function updatePanelGroup(server_id, group_id, { name, description, parent_group_id, permissions }) {
  return request('PUT', `/api/servers/${server_id}/panel-groups/${group_id}`, { name, description, parent_group_id, permissions })
}

/** 删除面板权限组（服主） */
export function deletePanelGroup(server_id, group_id) {
  return request('DELETE', `/api/servers/${server_id}/panel-groups/${group_id}`)
}

/** 获取成员当前分配的面板权限组 */
export function getMemberPanelGroup(server_id, user_id) {
  return request('GET', `/api/servers/${server_id}/members/${user_id}/panel-group`)
}

/** 分配成员到面板权限组（服主/网页管理员） */
export function assignMemberPanelGroup(server_id, user_id, group_id) {
  return request('PUT', `/api/servers/${server_id}/members/${user_id}/panel-group`, { group_id })
}

// ── 面板功能管理 ─────────────────────────────────────────────────────────────

/** 获取面板功能配置 */
export function getPanelFeatures(server_id) {
  return request('GET', `/api/servers/${server_id}/panel-features`)
}

/** 更新面板功能配置 */
export function updatePanelFeatures(server_id, {
  register_limit,
  blacklist_auto_reject_count = 0,
  character_name_regex,
  character_name_max_length,
}) {
  return request('PUT', `/api/servers/${server_id}/panel-features`, {
    register_limit,
    blacklist_auto_reject_count,
    character_name_regex,
    character_name_max_length,
  })
}

/** 更新入服审核开关（面板功能） */
export function updateJoinApproval(server_id, join_requires_approval) {
  return request('PUT', `/api/servers/${server_id}/panel-features/join-approval`, { join_requires_approval })
}

/** 面板功能：列出入服申请 */
export function listPanelJoinRequests(server_id, status) {
  const q = new URLSearchParams()
  if (status) q.set('status', status)
  const suffix = q.toString() ? `?${q.toString()}` : ''
  return request('GET', `/api/servers/${server_id}/panel-features/join-requests${suffix}`)
}

/** 面板功能：批准入服申请 */
export function approvePanelJoinRequest(server_id, request_id, note = '') {
  return request('POST', `/api/servers/${server_id}/panel-features/join-requests/${request_id}/approve`, { note })
}

/** 面板功能：拒绝入服申请 */
export function rejectPanelJoinRequest(server_id, request_id, note = '') {
  return request('POST', `/api/servers/${server_id}/panel-features/join-requests/${request_id}/reject`, { note })
}

/** 面板功能：发送邀请 */
export function createPanelInvite(server_id, invitee_email, message = '', expires_in_hours = 72) {
  return request('POST', `/api/servers/${server_id}/panel-features/invites`, {
    invitee_email,
    message,
    expires_in_hours,
  })
}

export function listServerBlacklist(server_id, query = {}) {
  const q = new URLSearchParams()
  if (query.q) q.set('q', query.q)
  const suffix = q.toString() ? `?${q.toString()}` : ''
  return request('GET', `/api/servers/${server_id}/blacklist${suffix}`)
}

export function addServerBlacklist(server_id, target_user_id, reason = '') {
  return request('POST', `/api/servers/${server_id}/blacklist`, { target_user_id, reason })
}

export function removeServerBlacklist(server_id, entry_id) {
  return request('DELETE', `/api/servers/${server_id}/blacklist/${entry_id}`)
}

export function submitCloudBlacklist(server_id, target_user_id, reason) {
  return request('POST', `/api/servers/${server_id}/cloud-blacklist-submissions`, { target_user_id, reason })
}
