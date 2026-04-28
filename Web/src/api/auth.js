import { apiUrl } from '@/api/base'

// ── 后端基础 URL 配置 ──────────────────────────────────────────
// 开发环境下通常配置为 localhost:8000

// ── 认证令牌与用户信息存储键名 ──────────────────────────────────
const TOKEN_KEY = 'ts_token'
const EMAIL_KEY = 'ts_email'

/** 获取存储在本地的 Token */
export function getToken()  { return localStorage.getItem(TOKEN_KEY) }

/** 获取存储在本地的邮箱 */
export function getEmail()  { return localStorage.getItem(EMAIL_KEY) }

/** 保存登录认证信息 */
export function saveAuth(token, email) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(EMAIL_KEY, email)
}

/** 清除本地认证信息 (登出时调用) */
export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(EMAIL_KEY)
}

// ── 通用 HTTP POST 请求封装 ────────────────────────────────────
async function post(path, body) {
  const res = await fetch(apiUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  const data = await res.json()
  if (!res.ok) {
    const err = new Error(data.detail || '请求失败')
    err.status = res.status
    throw err
  }
  return data
}

function authHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getToken()}`,
  }
}

async function get(path, withAuth = false) {
  const res = await fetch(apiUrl(path), {
    method: 'GET',
    headers: withAuth ? authHeaders() : undefined,
  })
  const data = await res.json()
  if (!res.ok) {
    const err = new Error(data.detail || '请求失败')
    err.status = res.status
    throw err
  }
  return data
}

async function postAuth(path, body) {
  const res = await fetch(apiUrl(path), {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(body),
  })
  const data = await res.json()
  if (!res.ok) {
    const err = new Error(data.detail || '请求失败')
    err.status = res.status
    throw err
  }
  return data
}

// ── 用户认证相关 API 接口 ──────────────────────────────────────

/** 
 * 发送注册验证码 
 * @param {string} email 
 * @param {string} password 
 */
export function sendCode(email, password) {
  return post('/api/auth/send-code', { email, password })
}

/** 
 * 提交注册（校验验证码）
 * @param {string} email 
 * @param {string} password 
 * @param {string} code 
 */
export function register(email, password, code) {
  return post('/api/auth/register', { email, password, code })
}

/** 
 * 用户登录 
 * @param {string} email 
 * @param {string} password 
 */
export function login(email, password) {
  return post('/api/auth/login', { email, password })
}

export function getBootstrapStatus() {
  return get('/api/auth/bootstrap-status')
}

export function bootstrapPlatformAdmin(bootstrap_token) {
  return postAuth('/api/auth/bootstrap-platform-admin', { bootstrap_token })
}

export function bootstrapSendCode(email, password, bootstrap_token) {
  return post(`/api/auth/bootstrap-send-code?bootstrap_token=${encodeURIComponent(bootstrap_token)}`, { email, password })
}

export function bootstrapRegister(email, password, code, bootstrap_token) {
  return post(`/api/auth/bootstrap-register?bootstrap_token=${encodeURIComponent(bootstrap_token)}`, { email, password, code })
}

export function getCurrentUser() {
  return get('/api/auth/me', true)
}

/**
 * 忘记密码：发送重置验证码
 * @param {string} email
 */
export function resetSendCode(email) {
  return post('/api/auth/reset-send-code', { email })
}

/**
 * 忘记密码：验证码校验 + 设置新密码
 * @param {string} email
 * @param {string} code
 * @param {string} new_password
 */
export function resetConfirm(email, code, new_password) {
  return post('/api/auth/reset-confirm', { email, code, new_password })
}
