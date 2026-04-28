import { getToken } from '@/api/auth'
import { apiUrl } from '@/api/base'

function authHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getToken()}`,
  }
}

function buildQuery(query = {}) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query || {})) {
    if (value === undefined || value === null || value === '') continue
    params.set(key, String(value))
  }
  const suffix = params.toString()
  return suffix ? `?${suffix}` : ''
}

async function request(method, path, { query, body } = {}) {
  const res = await fetch(apiUrl(`${path}${buildQuery(query)}`), {
    method,
    headers: authHeaders(),
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (res.status === 204) return null

  let data = null
  try {
    data = await res.json()
  } catch {
    throw new Error(`服务器错误 (${res.status})`)
  }

  if (!res.ok) throw new Error(data?.detail || '请求失败')
  return data
}

export function getPlatformStats() {
  return request('GET', '/api/platform/stats')
}

export function getPlatformMe() {
  return request('GET', '/api/platform/me')
}

export function listPlatformPermissions() {
  return request('GET', '/api/platform/permissions')
}

export function listPlatformServers(query = {}) {
  return request('GET', '/api/platform/servers/platform', { query })
}

export function getPlatformServerDetail(serverId) {
  return request('GET', `/api/platform/servers/${serverId}`)
}

export function auditPlatformServer(serverId, action, reason = '') {
  return request('POST', `/api/platform/servers/${serverId}/audit`, {
    query: { action, reason },
  })
}

export function publishPlatformServer(serverId) {
  return request('POST', `/api/platform/servers/${serverId}/publish`)
}

export function unpublishPlatformServer(serverId) {
  return request('POST', `/api/platform/servers/${serverId}/unpublish`)
}

export function deletePlatformServer(serverId, reason) {
  return request('DELETE', `/api/platform/servers/${serverId}`, {
    query: { reason },
  })
}

export function hardDeletePlatformServer(serverId, reason) {
  return request('DELETE', `/api/platform/servers/${serverId}/hard`, {
    query: { reason },
  })
}

export function updatePlatformServerStatus(serverId, platform_status, reason = '') {
  return request('POST', `/api/platform/servers/${serverId}/status`, {
    query: { platform_status, reason },
  })
}

export function listPlatformAccounts(query = {}) {
  return request('GET', '/api/platform/accounts', { query })
}

export function getPlatformAccountDetail(userId) {
  return request('GET', `/api/platform/accounts/${userId}`)
}

export function banPlatformAccount(userId, reason) {
  return request('POST', `/api/platform/accounts/${userId}/ban`, {
    query: { reason },
  })
}

export function unbanPlatformAccount(userId, reason = '') {
  return request('POST', `/api/platform/accounts/${userId}/unban`, {
    query: { reason },
  })
}

export function removePlatformAccountFromServer(userId, serverId, reason) {
  return request('DELETE', `/api/platform/accounts/${userId}/servers/${serverId}/membership`, {
    query: { reason },
  })
}

export function listAccountRestrictions(query = {}) {
  return request('GET', '/api/platform/account-restrictions', { query })
}

export function createAccountRestriction(payload) {
  return request('POST', '/api/platform/account-restrictions', { query: payload })
}

export function removeAccountRestriction(restrictionId) {
  return request('DELETE', `/api/platform/account-restrictions/${restrictionId}`)
}

export function listCloudBlacklistSubmissions(query = {}) {
  return request('GET', '/api/platform/cloud-blacklist-submissions', { query })
}

export function reviewCloudBlacklistSubmission(submissionId, action, review_note = '') {
  return request('POST', `/api/platform/cloud-blacklist-submissions/${submissionId}/review`, {
    body: { action, review_note },
  })
}

export function deleteCloudBlacklistSubmission(submissionId) {
  return request('DELETE', `/api/platform/cloud-blacklist-submissions/${submissionId}`)
}

export function listReports(query = {}) {
  return request('GET', '/api/platform/reports', { query })
}

export function resolveReport(reportId, payload) {
  return request('POST', `/api/platform/reports/${reportId}/resolve`, {
    query: payload,
  })
}

export function listOperationLogs(query = {}) {
  return request('GET', '/api/platform/operation-logs', { query })
}

export function listAnnouncements(query = {}) {
  return request('GET', '/api/platform/announcements', { query })
}

export function createAnnouncement(payload) {
  return request('POST', '/api/platform/announcements', { query: payload })
}

export function updateAnnouncement(announcementId, payload) {
  return request('PUT', `/api/platform/announcements/${announcementId}`, {
    query: payload,
  })
}

export function deleteAnnouncement(announcementId) {
  return request('DELETE', `/api/platform/announcements/${announcementId}`)
}

export function getPlatformSettings(key = '') {
  return request('GET', '/api/platform/platform-settings', {
    query: key ? { key } : {},
  })
}

export function updatePlatformSetting(key, payload) {
  return request('PUT', `/api/platform/platform-settings/${encodeURIComponent(key)}`, {
    query: payload,
  })
}

export function listPlatformUsers(query = {}) {
  return request('GET', '/api/platform/platform-users', { query })
}

export function listPlatformPermissionGroups() {
  return request('GET', '/api/platform/platform-permission-groups')
}

export function createPlatformPermissionGroup(payload) {
  return request('POST', '/api/platform/platform-permission-groups', {
    query: { ...payload, permissions: JSON.stringify(payload.permissions || []) },
  })
}

export function updatePlatformPermissionGroup(groupId, payload) {
  return request('PUT', `/api/platform/platform-permission-groups/${groupId}`, {
    query: { ...payload, permissions: JSON.stringify(payload.permissions || []) },
  })
}

export function deletePlatformPermissionGroup(groupId) {
  return request('DELETE', `/api/platform/platform-permission-groups/${groupId}`)
}

export function listPlatformPermissionGroupMembers(groupId) {
  return request('GET', `/api/platform/platform-permission-groups/${groupId}/members`)
}

export function addPlatformPermissionGroupMember(groupId, userId) {
  return request('POST', `/api/platform/platform-permission-groups/${groupId}/members/${userId}`)
}

export function removePlatformPermissionGroupMember(groupId, userId) {
  return request('DELETE', `/api/platform/platform-permission-groups/${groupId}/members/${userId}`)
}

export function grantPlatformAdmin(userId) {
  return request('POST', `/api/platform/platform-users/${userId}/admin`)
}

export function revokePlatformAdmin(userId) {
  return request('DELETE', `/api/platform/platform-users/${userId}/admin`)
}

export function updatePlatformUserPermissions(userId, permissions) {
  return request('PUT', `/api/platform/platform-users/${userId}/permissions`, {
    query: { permissions: JSON.stringify(permissions || []) },
  })
}
