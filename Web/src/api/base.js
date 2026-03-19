function normalizeBase(raw) {
  const v = String(raw || '').trim()
  if (!v || v === '/') return ''
  return v.replace(/\/+$/, '')
}

export const API_BASE = normalizeBase(import.meta.env.VITE_API_BASE)

export function apiUrl(path) {
  const p = String(path || '')
  const normalizedPath = p.startsWith('/') ? p : `/${p}`
  return `${API_BASE}${normalizedPath}`
}
