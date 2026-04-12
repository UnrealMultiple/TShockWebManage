/**
 * Terraria ID 名称映射工具
 * 从 /TerrariaID.json 中加载物品、图格、弹幕的 ID → 中文名 映射
 */

let _cache = null

async function loadTerrariaIDs() {
  if (_cache) return _cache
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}TerrariaID.json`)
    const data = await res.json()

    // 物品：{ id → { zhName, enName } }
    const itemMap = {}
    const itemList = []
    for (const entry of (data['物品'] || [])) {
      if (!itemMap[entry.ID]) {
        itemMap[entry.ID] = { zhName: entry['中文名称'] || '', enName: entry['英文名称'] || '' }
        itemList.push({ id: entry.ID, zhName: entry['中文名称'] || '', enName: entry['英文名称'] || '' })
      }
    }

    // 图格：同一 ID 可能有多个子ID，取第一个
    const tileMap = {}
    const tileList = []
    for (const entry of (data['图格'] || [])) {
      if (!tileMap[entry.ID]) {
        tileMap[entry.ID] = { zhName: entry['中文名称'] || '', enName: entry['英文名称'] || '' }
        tileList.push({ id: entry.ID, zhName: entry['中文名称'] || '', enName: entry['英文名称'] || '' })
      }
    }

    // 弹幕
    const projMap = {}
    const projList = []
    for (const entry of (data['弹幕'] || [])) {
      if (!projMap[entry.ID]) {
        projMap[entry.ID] = { zhName: entry['中文名称'] || '', enName: entry['英文名称'] || '' }
        projList.push({ id: entry.ID, zhName: entry['中文名称'] || '', enName: entry['英文名称'] || '' })
      }
    }

    _cache = { itemMap, itemList, tileMap, tileList, projMap, projList }
    return _cache
  } catch (e) {
    console.error('Failed to load TerrariaID.json', e)
    return { itemMap: {}, itemList: [], tileMap: {}, tileList: [], projMap: {}, projList: [] }
  }
}

/**
 * 根据类型和 ID 获取中文名
 * @param {'tile'|'item'|'proj'} type
 * @param {number} id
 * @param {{ itemMap, tileMap, projMap }} maps
 */
export function getZhName(type, id, maps) {
  if (!maps) return ''
  const map = type === 'item' ? maps.itemMap : type === 'tile' ? maps.tileMap : maps.projMap
  return map?.[id]?.zhName || ''
}

/**
 * 根据类型获取完整列表（用于搜索选择）
 * @param {'tile'|'item'|'proj'} type
 * @param {{ itemList, tileList, projList }} maps
 */
export function getListByType(type, maps) {
  if (!maps) return []
  if (type === 'item') return maps.itemList
  if (type === 'tile') return maps.tileList
  return maps.projList
}

export { loadTerrariaIDs }
