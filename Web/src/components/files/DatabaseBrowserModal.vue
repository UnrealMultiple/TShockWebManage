<template>
  <div :class="embedded ? 'db-embed' : 'modal-backdrop'" @click.self="embedded ? null : close()">
    <div :class="['db-modal', { embedded }]">
      <div class="db-header">
        <div class="db-title-row">
          <span class="db-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
          </span>
          <span class="db-filename">{{ file.name }}</span>
          <span class="db-badge">SQLite</span>
        </div>
        <div class="db-header-tabs">
          <button :class="['db-view-btn', { active: dbViewMode === 'table' }]" @click="dbViewMode = 'table'">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
            表格
          </button>
          <button
            v-if="canUseRawSql"
            :class="['db-view-btn', { active: dbViewMode === 'sql' }]"
            @click="dbViewMode = 'sql'"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            SQL
          </button>
        </div>
        <button v-if="!embedded" class="em-close" @click="close" title="关闭">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <div class="db-body">
        <div class="db-sidebar">
          <div class="db-sidebar-hd">
            <span>数据表</span>
            <div v-if="dbTablesLoading" class="spinner spinner-xs"></div>
          </div>
          <div v-if="dbTablesErr" class="db-sidebar-err">{{ dbTablesErr }}</div>
          <button
            v-for="t in dbTables"
            :key="t"
            :class="['db-tbl-item', { active: dbActiveTable === t }]"
            @click="selectTable(t)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <line x1="3" y1="9" x2="21" y2="9"/>
              <line x1="3" y1="15" x2="21" y2="15"/>
            </svg>
            {{ t }}
          </button>
          <div v-if="!dbTablesLoading && dbTables.length === 0 && !dbTablesErr" class="db-sidebar-empty">暂无表</div>
        </div>

        <div class="db-main">
          <template v-if="dbViewMode === 'sql'">
            <div class="db-sql-wrap">
              <textarea
                class="db-sql-input"
                v-model="dbSqlInput"
                rows="3"
                placeholder="输入 SQL（SELECT … 或 INSERT / UPDATE / DELETE），Ctrl+Enter 执行"
                @keydown.ctrl.enter.prevent="runDbSql"
              ></textarea>
              <div class="db-sql-btns">
                <button class="db-run-btn" @click="runDbSql" :disabled="dbRunning">
                  <svg v-if="!dbRunning" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z"/>
                  </svg>
                  {{ dbRunning ? '执行中…' : '执行' }}
                </button>
                <button class="db-clear-btn" @click="clearSql">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                  清空
                </button>
              </div>
            </div>
            <div class="db-result-area">
              <div v-if="dbRunning" class="db-result-loading">
                <div class="spinner spinner-md"></div>
                <span>执行中…</span>
              </div>
              <div v-else-if="dbResultErr" class="db-result-err">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                {{ dbResultErr }}
              </div>
              <template v-else-if="dbResult">
                <div v-if="dbResult.type === 'query'">
                  <div class="db-result-meta">返回 <strong>{{ dbResult.rows.length }}</strong> 行<span v-if="dbResult.truncated" class="db-truncated-hint">（已截断，最多 500 行）</span></div>
                  <div class="db-table-wrap">
                    <table class="db-table">
                      <thead><tr><th v-for="c in dbResult.columns" :key="c">{{ c }}</th></tr></thead>
                      <tbody>
                        <tr v-for="(row, ri) in dbResult.rows" :key="ri">
                          <td v-for="(cell, ci) in row" :key="ci" :class="{ 'db-null': cell === null }">{{ cell === null ? 'NULL' : cell }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
                <div v-else-if="dbResult.type === 'exec'" class="db-exec-ok">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                    <polyline points="22 4 12 14.01 9 11.01"/>
                  </svg>
                  执行成功，影响 <strong>{{ dbResult.affected }}</strong> 行
                </div>
              </template>
              <div v-else class="db-result-empty">在上方输入 SQL 后点击“执行”或按 Ctrl+Enter</div>
            </div>
          </template>

          <template v-else>
            <div v-if="!dbActiveTable" class="db-no-table">从左侧选择数据表</div>
            <template v-else>
              <div class="db-tbl-toolbar">
                <span class="db-tbl-name">{{ dbActiveTable }}</span>
                <span v-if="dbTableCols.length" class="db-col-badge">{{ dbTableCols.length }} 列</span>
                <span class="db-spacer"></span>
                <span v-if="dbResultErr" class="db-tbl-err">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                    <line x1="12" y1="9" x2="12" y2="13"/>
                    <line x1="12" y1="17" x2="12.01" y2="17"/>
                  </svg>
                  {{ dbResultErr }}
                </span>
                <button v-if="canWriteDatabase" class="db-add-row-btn" @click="startAddRow" :disabled="dbTableLoading">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="12" y1="5" x2="12" y2="19"/>
                    <line x1="5" y1="12" x2="19" y2="12"/>
                  </svg>
                  添加行
                </button>
                <button class="db-pg-btn" @click="dbPagePrev" :disabled="dbPage === 0 || dbTableLoading" title="上一页">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="15 18 9 12 15 6"/>
                  </svg>
                </button>
                <span class="db-pg-info">第 {{ dbPage + 1 }} 页</span>
                <button class="db-pg-btn" @click="dbPageNext" :disabled="!dbHasMore || dbTableLoading" title="下一页">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="9 18 15 12 9 6"/>
                  </svg>
                </button>
                <button class="db-reload-btn" @click="loadTableData" :disabled="dbTableLoading" title="刷新">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/></svg>
                </button>
              </div>

              <div class="db-visual-wrap">
                <div v-if="dbTableLoading" class="db-result-loading">
                  <div class="spinner spinner-md"></div>
                  <span>加载中…</span>
                </div>
                <table v-else class="db-visual-table">
                  <thead>
                    <tr>
                      <th v-for="col in dbTableCols" :key="col.name" class="db-vth">
                        <span class="db-col-nm">{{ col.name }}</span>
                        <span class="db-col-tp">{{ col.type }}</span>
                        <span v-if="col.pk" class="db-pk">PK</span>
                      </th>
                      <th v-if="canWriteDatabase" class="db-ops-th">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-if="canWriteDatabase && dbAddRowMode" class="db-add-row-tr">
                      <td v-for="col in dbTableCols" :key="col.name" class="db-add-td">
                        <input class="db-cell-inp" v-model="dbNewRowValues[col.name]" :placeholder="col.dflt ?? col.type" />
                      </td>
                      <td class="db-ops-cell">
                        <button class="db-ok-btn" @click="confirmAddRow" :disabled="dbAddRowSaving" title="确认">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="20 6 9 17 4 12"/>
                          </svg>
                        </button>
                        <button class="db-cx-btn" @click="dbAddRowMode = false" title="取消">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"/>
                            <line x1="6" y1="6" x2="18" y2="18"/>
                          </svg>
                        </button>
                      </td>
                    </tr>
                    <tr v-for="(row, ri) in dbTableRows" :key="row[0]">
                      <td
                        v-for="(col, ci) in dbTableCols"
                        :key="col.name"
                        :class="['db-vtd', { 'db-null': row[ci+1] === null, 'db-cell-active': dbEditCell && dbEditCell.rowIdx === ri && dbEditCell.colIdx === ci }]"
                        @dblclick="canWriteDatabase ? startEditCell(ri, ci, row[ci+1]) : null"
                      >
                        <template v-if="dbEditCell && dbEditCell.rowIdx === ri && dbEditCell.colIdx === ci">
                          <input
                            class="db-cell-inp db-cell-inp-edit"
                            v-model="dbEditCell.value"
                            @keydown.enter.prevent="saveEditCell"
                            @keydown.escape="cancelEditCell"
                            @blur="saveEditCell"
                            ref="dbCellInputRef"
                          />
                        </template>
                        <template v-else>
                          <span class="db-cv">{{ row[ci+1] === null ? 'NULL' : row[ci+1] }}</span>
                        </template>
                      </td>
                      <td v-if="canWriteDatabase" class="db-ops-cell">
                        <button class="db-del-row-btn" @click="deleteRow(ri, row[0])" title="删除此行">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6l-1 14H6L5 6"/>
                            <path d="M10 11v6"/>
                            <path d="M14 11v6"/>
                            <path d="M9 6V4h6v2"/>
                          </svg>
                        </button>
                      </td>
                    </tr>
                    <tr v-if="dbTableRows.length === 0 && !dbTableLoading">
                      <td :colspan="dbTableCols.length + (canWriteDatabase ? 1 : 0)" class="db-empty-row">该表暂无数据</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useFeedback } from '@/composables/useFeedback'

const props = defineProps({
  file: { type: Object, required: true },
  activeServerKey: { type: String, default: '' },
  canWriteDatabase: { type: Boolean, default: false },
  canUseRawSql: { type: Boolean, default: false },
  embedded: { type: Boolean, default: false },
})

const emit = defineEmits(['close'])
const { toast, dialog } = useFeedback()

const dbTables = ref([])
const dbTablesLoading = ref(false)
const dbTablesErr = ref('')
const dbActiveTable = ref('')
const dbSqlInput = ref('')
const dbRunning = ref(false)
const dbResult = ref(null)
const dbResultErr = ref('')
const dbViewMode = ref('table')
const dbTableCols = ref([])
const dbTableRows = ref([])
const dbTableLoading = ref(false)
const dbHasMore = ref(false)
const dbPage = ref(0)
const dbPageSize = 200
const dbEditCell = ref(null)
const dbEditSaving = ref(false)
const dbAddRowMode = ref(false)
const dbNewRowValues = ref({})
const dbAddRowSaving = ref(false)
const dbCellInputRef = ref(null)
let mounted = false

function send(type, msgId, payload) {
  window.__tshockSend?.({
    type,
    msg_id: msgId,
    timestamp: Date.now(),
    payload: { agent_key: props.activeServerKey, ...payload },
  })
}

function resetAndLoad() {
  dbTables.value = []
  dbTablesLoading.value = true
  dbTablesErr.value = ''
  dbActiveTable.value = ''
  dbSqlInput.value = ''
  dbRunning.value = false
  dbResult.value = null
  dbResultErr.value = ''
  dbViewMode.value = 'table'
  dbTableCols.value = []
  dbTableRows.value = []
  dbTableLoading.value = false
  dbHasMore.value = false
  dbPage.value = 0
  dbEditCell.value = null
  dbEditSaving.value = false
  dbAddRowMode.value = false
  dbAddRowSaving.value = false
  dbNewRowValues.value = {}
  send('db_query', 'dbtables-' + Date.now(), {
    path: props.file.full_path,
    sql: "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
  })
}

function close() {
  emit('close')
}

function clearSql() {
  dbSqlInput.value = ''
  dbResult.value = null
  dbResultErr.value = ''
}

function selectTable(t) {
  dbActiveTable.value = t
  dbViewMode.value = 'table'
  dbPage.value = 0
  dbEditCell.value = null
  dbAddRowMode.value = false
  dbResultErr.value = ''
  dbTableCols.value = []
  dbTableRows.value = []
  dbTableLoading.value = true
  const safeT = t.replace(/"/g, '""')
  send('db_query', 'dbinfo-' + Date.now(), {
    path: props.file.full_path,
    sql: `PRAGMA table_info("${safeT}")`,
  })
  loadTableData()
}

function loadTableData() {
  if (!dbActiveTable.value || !props.file) return
  dbTableLoading.value = true
  const safeT = dbActiveTable.value.replace(/"/g, '""')
  const offset = dbPage.value * dbPageSize
  send('db_query', 'dbdata-' + Date.now(), {
    path: props.file.full_path,
    sql: `SELECT rowid AS __rowid__, * FROM "${safeT}" LIMIT ${dbPageSize + 1} OFFSET ${offset}`,
  })
}

function dbPagePrev() {
  if (dbPage.value > 0) {
    dbPage.value--
    loadTableData()
  }
}

function dbPageNext() {
  if (dbHasMore.value) {
    dbPage.value++
    loadTableData()
  }
}

function startEditCell(ri, ci, val) {
  if (!props.canWriteDatabase) {
    toast.warning('缺少数据库写入权限')
    return
  }
  if (dbEditSaving.value) return
  dbEditCell.value = { rowIdx: ri, colIdx: ci, value: val === null ? '' : String(val), orig: val }
  nextTick(() => {
    const inp = dbCellInputRef.value
    ;(Array.isArray(inp) ? inp[0] : inp)?.focus?.()
  })
}

function cancelEditCell() {
  dbEditCell.value = null
}

function saveEditCell() {
  if (!props.canWriteDatabase) {
    toast.warning('缺少数据库写入权限')
    return
  }
  if (!dbEditCell.value || !props.file) return
  const { rowIdx, colIdx, value, orig } = dbEditCell.value
  const newVal = value === '' ? null : value
  if (String(newVal) === String(orig) || (newVal === null && orig === null)) {
    dbEditCell.value = null
    return
  }
  const row = dbTableRows.value[rowIdx]
  const col = dbTableCols.value[colIdx]?.name
  const rowid = row?.[0]
  if (!col) {
    dbEditCell.value = null
    return
  }
  dbEditSaving.value = true
  send('db_update_row', 'dbedit-' + Date.now(), {
    path: props.file.full_path,
    table: dbActiveTable.value,
    rowid,
    col,
    value: newVal,
  })
}

async function deleteRow(rowIdx, rowid) {
  if (!props.canWriteDatabase) {
    toast.warning('缺少数据库写入权限')
    return
  }
  const ok = await dialog.confirm({
    title: '删除数据行',
    message: '确认删除此行？',
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  dbTableRows.value.splice(rowIdx, 1)
  send('db_delete_row', 'dbdel-' + Date.now(), {
    path: props.file.full_path,
    table: dbActiveTable.value,
    rowid,
  })
}

function startAddRow() {
  if (!props.canWriteDatabase) {
    toast.warning('缺少数据库写入权限')
    return
  }
  dbAddRowMode.value = true
  const vals = {}
  dbTableCols.value.forEach(c => { vals[c.name] = '' })
  dbNewRowValues.value = vals
}

function confirmAddRow() {
  if (!props.canWriteDatabase) {
    toast.warning('缺少数据库写入权限')
    return
  }
  if (!props.file) return
  dbAddRowSaving.value = true
  const cols = dbTableCols.value.map(c => c.name).filter(c => dbNewRowValues.value[c] !== '')
  const vals = cols.map(c => {
    const v = dbNewRowValues.value[c]
    return v === '' ? null : v
  })
  send('db_insert_row', 'dbins-' + Date.now(), {
    path: props.file.full_path,
    table: dbActiveTable.value,
    cols,
    values: vals,
  })
}

async function runDbSql() {
  if (!props.canUseRawSql) {
    toast.warning('缺少原始 SQL 权限')
    return
  }
  if (!dbSqlInput.value.trim() || !props.file) return
  const sql = dbSqlInput.value.trim()
  const isSelect = /^\s*select\b/i.test(sql)
  if (!isSelect) {
    const ok = await dialog.confirm({
      title: '执行 SQL 变更',
      message: '该 SQL 可能修改数据库。确认执行？',
      confirmText: '执行',
      danger: true,
    })
    if (!ok) return
  }
  dbRunning.value = true
  dbResultErr.value = ''
  dbResult.value = null
  send(isSelect ? 'db_query' : 'db_exec', 'dbrun-' + Date.now(), {
    path: props.file.full_path,
    sql,
  })
}

function onWsMessage(e) {
  const pkt = e.detail
  const p = pkt.payload || {}

  if (pkt.type === 'db_query_resp') {
    const refId = p.ref_id ?? ''
    if (refId.startsWith('dbtables-')) {
      dbTablesLoading.value = false
      if (p.success) {
        dbTables.value = (p.rows || []).map(r => r[0])
        dbTablesErr.value = ''
        if (dbTables.value.length > 0) selectTable(dbTables.value[0])
      } else {
        dbTablesErr.value = p.msg || '获取表列表失败'
      }
    } else if (refId.startsWith('dbinfo-')) {
      if (p.success) {
        dbTableCols.value = (p.rows || []).map(r => ({
          cid: r[0],
          name: r[1],
          type: r[2] || '',
          notnull: r[3],
          dflt: r[4],
          pk: r[5],
        }))
      }
    } else if (refId.startsWith('dbdata-')) {
      dbTableLoading.value = false
      if (p.success) {
        const rows = p.rows || []
        dbHasMore.value = rows.length > dbPageSize
        dbTableRows.value = dbHasMore.value ? rows.slice(0, dbPageSize) : rows
      } else {
        dbResultErr.value = p.msg || '查询失败'
      }
    } else {
      dbRunning.value = false
      if (p.success) {
        dbResult.value = { type: 'query', columns: p.columns, rows: p.rows, truncated: p.truncated }
        dbResultErr.value = ''
      } else {
        dbResultErr.value = p.msg || '查询失败'
      }
    }
    return
  }

  if (pkt.type === 'db_exec_resp') {
    dbRunning.value = false
    if (p.success) {
      dbResult.value = { type: 'exec', affected: p.affected }
      dbResultErr.value = ''
    } else {
      dbResultErr.value = p.msg || '执行失败'
    }
    return
  }

  if (pkt.type === 'db_update_row_resp') {
    dbEditSaving.value = false
    if (p.success) {
      const ec = dbEditCell.value
      if (ec && dbTableRows.value[ec.rowIdx]) {
        const row = [...dbTableRows.value[ec.rowIdx]]
        row[ec.colIdx + 1] = ec.value === '' ? null : ec.value
        dbTableRows.value[ec.rowIdx] = row
      }
      dbEditCell.value = null
    } else {
      dbEditCell.value = null
      dbResultErr.value = p.msg || '更新失败'
    }
    return
  }

  if (pkt.type === 'db_delete_row_resp') {
    if (!p.success) {
      dbResultErr.value = p.msg || '删除失败'
      loadTableData()
    }
    return
  }

  if (pkt.type === 'db_insert_row_resp') {
    dbAddRowSaving.value = false
    if (p.success) {
      dbAddRowMode.value = false
      dbNewRowValues.value = {}
      loadTableData()
    } else {
      dbResultErr.value = p.msg || '插入失败'
    }
  }
}

watch(
  () => props.file,
  () => {
    if (mounted) resetAndLoad()
  }
)

onMounted(() => {
  mounted = true
  window.addEventListener('ws-message', onWsMessage)
  resetAndLoad()
})

onUnmounted(() => {
  window.removeEventListener('ws-message', onWsMessage)
})
</script>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0; z-index: 2000;
  background: rgba(15, 23, 42, .55);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.db-embed {
  flex: 1;
  min-height: 0;
  display: flex;
  background: #fff;
}

.spinner {
  border: 3px solid #e2e8f0; border-top-color: #3b82f6;
  border-radius: 50%; animation: spin .8s linear infinite;
}
.spinner-xs { width: 12px; height: 12px; border-width: 2px; flex-shrink: 0; }
.spinner-md { width: 24px; height: 24px; border-width: 2px; }
@keyframes spin { to { transform: rotate(360deg); } }

.db-modal {
  background: #fff; border-radius: 14px;
  width: min(95vw, 1160px); height: min(88vh, 800px);
  display: flex; flex-direction: column;
  box-shadow: 0 25px 60px rgba(0,0,0,.25);
}
.db-modal.embedded {
  width: 100%;
  height: 100%;
  border-radius: 0;
  box-shadow: none;
}
.db-header {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 18px; border-bottom: 1px solid #e2e8f0; flex-shrink: 0;
}
.db-title-row { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
.db-icon {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; background: #f0fdf4; border-radius: 6px; flex-shrink: 0;
}
.db-icon svg { width: 16px; height: 16px; stroke: #16a34a; }
.db-filename { font-size: 15px; font-weight: 700; color: #0f172a; font-family: 'Courier New', monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.db-badge { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; flex-shrink: 0; }
.db-header-tabs { display: flex; gap: 4px; flex-shrink: 0; }
.db-view-btn {
  padding: 6px 12px; border-radius: 7px; font-size: 12px; font-weight: 500;
  background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0;
  cursor: pointer; transition: all .12s; white-space: nowrap;
  display: inline-flex; align-items: center; gap: 5px;
}
.db-view-btn svg { width: 13px; height: 13px; flex-shrink: 0; }
.db-view-btn:hover  { background: #e2e8f0; }
.db-view-btn.active { background: #eff6ff; color: #2563eb; border-color: #93c5fd; font-weight: 700; }
.em-close {
  display: inline-flex; align-items: center; justify-content: center;
  width: 30px; height: 30px;
  background: none; border: none; font-size: 18px; color: #94a3b8;
  cursor: pointer; padding: 2px 6px; border-radius: 6px; transition: all .12s; line-height: 1; flex-shrink: 0;
}
.em-close svg { width: 16px; height: 16px; }
.em-close:hover { background: #f1f5f9; color: #0f172a; }

.db-body { display: flex; flex: 1; min-height: 0; overflow: hidden; }
.db-sidebar {
  width: 160px; flex-shrink: 0; border-right: 1px solid #e2e8f0;
  overflow-y: auto; display: flex; flex-direction: column; background: #f8fafc;
}
.db-sidebar-hd {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px 8px;
  font-size: 11px; font-weight: 700; color: #64748b;
  letter-spacing: .06em; text-transform: uppercase;
  border-bottom: 1px solid #e2e8f0; flex-shrink: 0;
}
.db-tbl-item {
  display: flex; align-items: flex-start; gap: 5px;
  padding: 8px 12px; font-size: 12px; color: #334155;
  cursor: pointer; background: none; border: none; text-align: left; width: 100%;
  border-bottom: 1px solid #f1f5f9; transition: background .1s; word-break: break-all;
}
.db-tbl-item svg { width: 13px; height: 13px; flex-shrink: 0; margin-top: 1px; }
.db-tbl-item:hover  { background: #eff6ff; color: #2563eb; }
.db-tbl-item.active { background: #eff6ff; color: #2563eb; font-weight: 700; border-left: 3px solid #3b82f6; }
.db-sidebar-empty { padding: 18px 12px; font-size: 11px; color: #94a3b8; text-align: center; }
.db-sidebar-err   { padding: 8px 12px; font-size: 12px; color: #dc2626; }

.db-main { flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; }
.db-sql-wrap {
  display: flex; gap: 10px; align-items: flex-start;
  padding: 12px 16px; border-bottom: 1px solid #f1f5f9; flex-shrink: 0;
}
.db-sql-input {
  flex: 1; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px;
  font-family: 'Courier New', monospace; font-size: 13px; color: #1e293b;
  resize: none; outline: none; background: #f8fafc; line-height: 1.5;
}
.db-sql-input:focus { border-color: #93c5fd; background: #fff; }
.db-sql-btns { display: flex; flex-direction: column; gap: 6px; flex-shrink: 0; }
.db-run-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 5px;
  padding: 8px 18px; background: #2563eb; color: #fff;
  border: none; border-radius: 7px; font-size: 13px; font-weight: 600;
  cursor: pointer; white-space: nowrap; transition: background .12s;
}
.db-run-btn svg { width: 13px; height: 13px; flex-shrink: 0; }
.db-run-btn:hover:not(:disabled) { background: #1d4ed8; }
.db-run-btn:disabled { opacity: .5; cursor: not-allowed; }
.db-clear-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 5px;
  padding: 6px 14px; background: #f1f5f9; color: #64748b;
  border: 1px solid #e2e8f0; border-radius: 7px; font-size: 12px;
  cursor: pointer; transition: all .12s; text-align: center;
}
.db-clear-btn svg { width: 12px; height: 12px; flex-shrink: 0; }
.db-clear-btn:hover { background: #e2e8f0; }

.db-tbl-toolbar {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 8px 14px; border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0; background: #f8fafc; min-height: 44px;
}
.db-tbl-name { font-size: 14px; font-weight: 700; color: #0f172a; font-family: 'Courier New', monospace; }
.db-col-badge {
  font-size: 11px; color: #64748b;
  background: #e2e8f0; border-radius: 4px; padding: 1px 7px; font-weight: 600;
}
.db-spacer { flex: 1; }
.db-tbl-err { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; color: #dc2626; }
.db-tbl-err svg { width: 13px; height: 13px; flex-shrink: 0; }
.db-add-row-btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 12px; background: #ecfdf5; color: #15803d; border: 1px solid #86efac;
  border-radius: 6px; font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all .12s; white-space: nowrap;
}
.db-add-row-btn svg { width: 12px; height: 12px; flex-shrink: 0; }
.db-add-row-btn:hover:not(:disabled) { background: #dcfce7; }
.db-add-row-btn:disabled { opacity: .5; cursor: not-allowed; }
.db-pg-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 30px; height: 28px;
  padding: 4px 10px; background: #fff; color: #475569;
  border: 1px solid #e2e8f0; border-radius: 6px; font-size: 14px;
  cursor: pointer; transition: all .12s;
}
.db-pg-btn svg { width: 14px; height: 14px; flex-shrink: 0; }
.db-pg-btn:hover:not(:disabled) { background: #f1f5f9; }
.db-pg-btn:disabled { opacity: .4; cursor: not-allowed; }
.db-pg-info { font-size: 12px; color: #64748b; white-space: nowrap; }
.db-reload-btn {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 5px 8px; background: #fff; color: #64748b;
  border: 1px solid #e2e8f0; border-radius: 6px;
  cursor: pointer; transition: all .12s;
}
.db-reload-btn svg { width: 13px; height: 13px; }
.db-reload-btn:hover:not(:disabled) { background: #f1f5f9; }
.db-reload-btn:disabled { opacity: .4; cursor: not-allowed; }

.db-visual-wrap { flex: 1; overflow: auto; }
.db-visual-table {
  border-collapse: collapse; font-size: 12px; font-family: 'Courier New', monospace;
  width: 100%; white-space: nowrap;
}
.db-vth {
  background: #f8fafc; border: 1px solid #e2e8f0;
  padding: 7px 10px; text-align: left; position: sticky; top: 0; z-index: 1;
}
.db-col-nm { font-size: 12px; color: #334155; font-weight: 700; }
.db-col-tp { font-size: 10px; color: #94a3b8; margin-left: 5px; font-weight: 400; }
.db-pk {
  font-size: 10px; background: #fef3c7; color: #92400e; border: 1px solid #fde68a;
  border-radius: 3px; padding: 1px 4px; margin-left: 4px; font-weight: 700;
}
.db-ops-th {
  background: #f8fafc; border: 1px solid #e2e8f0;
  padding: 7px 10px; position: sticky; top: 0; z-index: 1;
  text-align: center; font-size: 11px; color: #94a3b8; width: 48px;
}
.db-vtd {
  border: 1px solid #f1f5f9; padding: 5px 10px; color: #334155;
  max-width: 260px; cursor: default; user-select: none;
}
.db-vtd:hover { background: #f8fafc; }
.db-cell-active { background: #eff6ff !important; outline: 2px solid #3b82f6; outline-offset: -1px; }
.db-null { color: #94a3b8 !important; font-style: italic; }
.db-ops-cell { border: 1px solid #f1f5f9; padding: 3px 6px; text-align: center; }
.db-add-row-tr { background: #f0fdf4; }
.db-add-td { border: 1px solid #86efac; padding: 4px 6px; }
.db-cell-inp {
  width: 100%; padding: 3px 6px; border: 1px solid #e2e8f0; border-radius: 4px;
  font-family: 'Courier New', monospace; font-size: 12px; outline: none;
  background: #fff; box-sizing: border-box;
}
.db-cell-inp:focus { border-color: #3b82f6; }
.db-cell-inp-edit { min-width: 120px; }
.db-cv { display: block; overflow: hidden; text-overflow: ellipsis; }
.db-ok-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 24px;
  padding: 3px 8px; background: #16a34a; color: #fff;
  border: none; border-radius: 4px; font-size: 13px; cursor: pointer;
}
.db-ok-btn svg { width: 13px; height: 13px; }
.db-ok-btn:hover { background: #15803d; }
.db-cx-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 24px;
  padding: 3px 8px; background: #f1f5f9; color: #475569;
  border: 1px solid #e2e8f0; border-radius: 4px; font-size: 13px; cursor: pointer; margin-left: 4px;
}
.db-cx-btn svg { width: 13px; height: 13px; }
.db-cx-btn:hover { background: #e2e8f0; }
.db-del-row-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 24px;
  padding: 2px 6px; background: none; color: #94a3b8;
  border: none; border-radius: 4px; font-size: 13px; cursor: pointer;
  transition: all .12s; opacity: 0;
}
.db-del-row-btn svg { width: 13px; height: 13px; }
tr:hover .db-del-row-btn { opacity: 1; }
.db-del-row-btn:hover { background: #fee2e2; color: #dc2626; }
.db-empty-row { text-align: center; padding: 32px; color: #94a3b8; font-size: 13px; }
.db-no-table {
  display: flex; align-items: center; justify-content: center;
  flex: 1; color: #94a3b8; font-size: 14px;
}

.db-result-area { flex: 1; overflow: hidden; display: flex; flex-direction: column; min-height: 0; }
.db-result-loading { display: flex; align-items: center; gap: 12px; padding: 32px; color: #94a3b8; justify-content: center; }
.db-result-err {
  display: flex; align-items: center; gap: 8px;
  margin: 14px 16px; padding: 10px 14px;
  background: #fff5f5; border: 1px solid #fecaca; border-radius: 8px;
  color: #dc2626; font-size: 13px; font-family: 'Courier New', monospace;
}
.db-result-err svg { width: 15px; height: 15px; flex-shrink: 0; }
.db-result-meta { padding: 10px 16px 6px; font-size: 13px; color: #475569; flex-shrink: 0; }
.db-truncated-hint { font-size: 11px; color: #f59e0b; margin-left: 8px; font-weight: 600; }
.db-table-wrap { flex: 1; overflow: auto; padding: 0 16px 12px; }
.db-table {
  border-collapse: collapse; font-size: 12px;
  font-family: 'Courier New', monospace; width: 100%; white-space: nowrap;
}
.db-table th {
  background: #f8fafc; border: 1px solid #e2e8f0;
  padding: 7px 12px; font-size: 11px; color: #64748b;
  font-weight: 700; text-align: left; letter-spacing: .04em; text-transform: uppercase;
  position: sticky; top: 0;
}
.db-table td { border: 1px solid #f1f5f9; padding: 5px 12px; color: #334155; max-width: 300px; overflow: hidden; text-overflow: ellipsis; }
.db-table tr:hover td { background: #f8fafc; }
.db-exec-ok {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 24px; font-size: 15px; color: #16a34a; text-align: center;
}
.db-exec-ok svg { width: 18px; height: 18px; flex-shrink: 0; }
.db-result-empty { padding: 40px; text-align: center; color: #94a3b8; font-size: 13px; }
</style>
