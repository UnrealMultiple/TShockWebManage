/**
 * 静态资源路径工具
 * 使用 import.meta.env.BASE_URL 适配 GitHub Pages 子路径部署
 */
const BASE = import.meta.env.BASE_URL

export function itemImage(id) {
  return `${BASE}items/${id}.png`
}

export function resourcePath(rel) {
  return `${BASE}resources/${rel}`
}

export { BASE }
