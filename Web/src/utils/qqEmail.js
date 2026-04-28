const QQ_NUMBER_RE = /^[1-9]\d{4,11}$/

export function normalizeQqEmailInput(value) {
  const raw = String(value || '').trim().toLowerCase()
  const qq = raw.endsWith('@qq.com') ? raw.slice(0, -7) : raw
  if (!qq || (raw.includes('@') && !raw.endsWith('@qq.com'))) return ''
  if (!QQ_NUMBER_RE.test(qq)) return ''
  return `${qq}@qq.com`
}

export function qqEmailInputError(label = 'QQ 号或 QQ 邮箱') {
  return `请输入正确的${label}`
}
