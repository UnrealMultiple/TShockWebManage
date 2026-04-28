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

export function listMessages({ unreadOnly = false, q = '', category = 'all', limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams({
    unread_only: unreadOnly ? 'true' : 'false',
    category,
    limit: String(limit),
    offset: String(offset),
  })
  if (q) params.set('q', q)
  return request('GET', `/api/messages?${params.toString()}`)
}

export function getUnreadCount() {
  return request('GET', '/api/messages/unread-count')
}

export function markMessageRead(messageId) {
  return request('POST', `/api/messages/${messageId}/read`)
}

export function markAllMessagesRead() {
  return request('POST', '/api/messages/read-all')
}

export function listMyJoinRequests(status = '') {
  const q = new URLSearchParams()
  if (status) q.set('status', status)
  const suffix = q.toString() ? `?${q.toString()}` : ''
  return request('GET', `/api/messages/join-requests${suffix}`)
}

export function withdrawMyJoinRequest(requestId) {
  return request('POST', `/api/messages/join-requests/${requestId}/withdraw`)
}

export function listMyInvites(status = 'pending') {
  const q = new URLSearchParams()
  if (status) q.set('status', status)
  const suffix = q.toString() ? `?${q.toString()}` : ''
  return request('GET', `/api/messages/invites${suffix}`)
}

export function respondInvite(inviteId, action, note = '') {
  return request('POST', `/api/messages/invites/${inviteId}/respond`, { action, note })
}
