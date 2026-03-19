import { getToken } from '@/api/auth'
import { apiUrl } from '@/api/base'

function authHeaders() {
  return {
    'Content-Type':  'application/json',
    'Authorization': `Bearer ${getToken()}`,
  }
}

async function request(method, path, body) {
  const options = { method, headers: authHeaders() }
  if (body !== undefined) options.body = JSON.stringify(body)
  const res = await fetch(apiUrl(path), options)
  let data
  try { data = await res.json() } catch { throw new Error(`服务器错误 (${res.status})`) }
  if (!res.ok) throw new Error(data.detail || '请求失败')
  return data
}

/** 列出可用数据库 */
export function listDatabases() {
  return request('GET', '/api/db/list')
}

/** 列出数据库的所有表 */
export function listTables(dbName) {
  return request('GET', `/api/db/${dbName}/tables`)
}

/** 分页查询表数据 */
export function queryTable(dbName, tableName, page = 1, pageSize = 50) {
  return request('GET', `/api/db/${dbName}/table/${tableName}?page=${page}&page_size=${pageSize}`)
}

/** 更新一行（按主键） */
export function updateRow(dbName, tableName, pkCol, pkVal, data) {
  return request('PUT', `/api/db/${dbName}/table/${tableName}/row`, { pk_col: pkCol, pk_val: pkVal, data })
}

/** 插入新行 */
export function insertRow(dbName, tableName, data) {
  return request('POST', `/api/db/${dbName}/table/${tableName}/row`, { data })
}

/** 删除一行（按主键） */
export function deleteRow(dbName, tableName, pkCol, pkVal) {
  return request('DELETE', `/api/db/${dbName}/table/${tableName}/row`, { pk_col: pkCol, pk_val: pkVal })
}
