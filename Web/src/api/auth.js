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
  if (!res.ok) throw new Error(data.detail || '请求失败')
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
