<template>
  <div class="db-root">
    <!-- 左侧：表列表 -->
    <aside class="db-sidebar">
      <div v-if="loadingTables" class="db-side-msg">加载中…</div>
      <div v-else-if="tablesError" class="db-side-msg err">{{ tablesError }}</div>
      <template v-else>
        <div class="db-section">
          <div class="db-name">
            <span class="db-dot dot-ok"></span>表列表
          </div>
          <div
            v-for="tbl in tables"
            :key="tbl"
            :class="['db-tbl-item', { active: activeTable === tbl }]"
            @click="selectTable(tbl)"
          >{{ tbl }}</div>
          <div v-if="tables.length === 0" class="db-tbl-msg">数据库中没有表</div>
        </div>
      </template>
    </aside>

    <!-- 右侧：数据表格 -->
    <main class="db-main">
      <div v-if="!activeTable" class="db-placeholder">从左侧选择一个表查看数据</div>
      <template v-else>
        <div class="db-toolbar">
          <span class="db-table-title">{{ activeTable }}</span>
          <span class="db-total">共 {{ rows.length }}{{ truncated ? '+' : '' }} 行</span>
        </div>

        <div v-if="loadingRows" class="db-rows-msg">加载中…</div>
        <div v-else-if="rowsError" class="db-rows-msg err">{{ rowsError }}</div>

        <div v-else class="db-table-wrap">
          <table class="db-table">
            <thead>
              <tr>
                <th v-for="col in columns" :key="col" class="db-th">{{ col }}</th>
                <th class="db-th th-action">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in rows" :key="idx" class="db-tr">
                <td v-for="col in columns" :key="col" class="db-td">
                  <span class="db-cell">{{ row[col] !== null ? row[col] : 'NULL' }}</span>
                </td>
                <td class="db-td td-action">
                  <button class="row-btn edit-btn" @click="openEdit(row)" title="编辑行">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 20h9"/>
                      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>
                    </svg>
                  </button>
                  <button class="row-btn del-btn" @click="openDeleteRow(row)" title="删除行">
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
              <tr v-if="rows.length === 0">
                <td :colspan="columns.length + 1" class="db-empty">（空表）</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </main>

    <!-- ── 编辑/插入行 Modal ── -->
    <div v-if="editModal" class="modal-mask" @click.self="editModal = false">
      <div class="modal-box">
        <div class="modal-title">编辑行</div>
        <div class="modal-fields">
          <label v-for="col in columns" :key="col" class="field-row">
            <span class="field-label">{{ col }}</span>
            <input
              v-model="editForm[col]"
              class="field-input"
            />
          </label>
        </div>
        <div v-if="editError" class="modal-err">{{ editError }}</div>
        <div class="modal-actions">
          <button class="db-btn" @click="editModal = false">取消</button>
          <button class="db-btn primary" :disabled="saving" @click="saveEdit">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useFeedback } from '@/composables/useFeedback'

const props = defineProps({
  agentKey: String,
  dbPath: String,
})

const { toast, dialog } = useFeedback()

const tables = ref([])
const loadingTables = ref(false)
const tablesError = ref('')

const activeTable = ref('')
const rows = ref([])
const columns = ref([])
const truncated = ref(false)
const loadingRows = ref(false)
const rowsError = ref('')

const editModal = ref(false)
const editForm = ref({})
const editTargetRow = ref(null)
const editError = ref('')
const saving = ref(false)

function escIdent(name) {
  return String(name || '').replace(/"/g, '""')
}

function wsRequest(respType, reqType, payload) {
  return new Promise((resolve, reject) => {
    const msgId = `db-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    let timer = null

    const cleanup = () => {
      if (timer) clearTimeout(timer)
      window.removeEventListener('ws-message', handler)
    }

    const handler = (e) => {
      const pkt = e.detail
      if (pkt?.type !== respType) return
      if (pkt?.payload?.ref_id !== msgId) return
      cleanup()
      if (pkt.payload?.success) resolve(pkt.payload)
      else reject(new Error(pkt.payload?.msg || '请求失败'))
    }

    window.addEventListener('ws-message', handler)
    window.__tshockSend?.({
      type: reqType,
      msg_id: msgId,
      timestamp: Date.now(),
      payload,
    })

    timer = setTimeout(() => {
      cleanup()
      reject(new Error('请求超时'))
    }, 10000)
  })
}

function wsQuery(sql) {
  return wsRequest('db_query_resp', 'db_query', {
    agent_key: props.agentKey,
    path: props.dbPath,
    sql,
  })
}

function wsUpdate(table, rowid, col, value) {
  return wsRequest('db_update_row_resp', 'db_update_row', {
    agent_key: props.agentKey,
    path: props.dbPath,
    table,
    rowid,
    col,
    value,
  })
}

function wsDelete(table, rowid) {
  return wsRequest('db_delete_row_resp', 'db_delete_row', {
    agent_key: props.agentKey,
    path: props.dbPath,
    table,
    rowid,
  })
}

async function loadTables() {
  if (!props.agentKey || !props.dbPath) return
  loadingTables.value = true
  tablesError.value = ''
  activeTable.value = ''
  rows.value = []
  columns.value = []

  try {
    const res = await wsQuery("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables.value = (res.rows || []).map(r => r[0]).filter(Boolean)
    if (tables.value.length > 0) {
      await selectTable(tables.value[0])
    }
  } catch (e) {
    tablesError.value = '无法加载表: ' + e.message
  } finally {
    loadingTables.value = false
  }
}

async function selectTable(tbl) {
  if (!tbl) return
  activeTable.value = tbl
  loadingRows.value = true
  rowsError.value = ''
  rows.value = []
  columns.value = []

  try {
    const sql = `SELECT rowid AS _rowid, * FROM "${escIdent(tbl)}" LIMIT 500`
    const res = await wsQuery(sql)
    const allCols = res.columns || []
    columns.value = allCols.filter(c => c !== '_rowid')

    rows.value = (res.rows || []).map(r => {
      const obj = { _rowid: r[allCols.indexOf('_rowid')] }
      for (const col of columns.value) {
        obj[col] = r[allCols.indexOf(col)]
      }
      return obj
    })
    truncated.value = !!res.truncated
  } catch (e) {
    rowsError.value = '加载数据失败: ' + e.message
  } finally {
    loadingRows.value = false
  }
}

function openEdit(row) {
  editTargetRow.value = row
  editForm.value = { ...row }
  editError.value = ''
  editModal.value = true
}

async function saveEdit() {
  if (!editTargetRow.value) return
  saving.value = true
  editError.value = ''

  try {
    for (const col of columns.value) {
      if (editForm.value[col] !== editTargetRow.value[col]) {
        await wsUpdate(activeTable.value, editTargetRow.value._rowid, col, editForm.value[col])
      }
    }
    editModal.value = false
    await selectTable(activeTable.value)
  } catch (e) {
    editError.value = '保存失败: ' + e.message
  } finally {
    saving.value = false
  }
}

async function openDeleteRow(row) {
  const ok = await dialog.confirm({
    title: '删除数据行',
    message: '确定要删除这行数据吗？',
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  try {
    await wsDelete(activeTable.value, row._rowid)
    await selectTable(activeTable.value)
  } catch (e) {
    toast.error('删除失败: ' + e.message)
  }
}

watch(() => props.dbPath, () => {
  loadTables()
})

onMounted(() => {
  loadTables()
})
</script>

<style scoped>
.db-root {
  display: flex;
  height: 100%;
  width: 100%;
  overflow: hidden;
  background: #0f172a;
  color: #e2e8f0;
  font-family: inherit;
}
.db-sidebar {
  width: 240px;
  background: #1e293b;
  border-right: 1px solid #334155;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.db-side-msg {
  padding: 20px;
  font-size: 13px;
  color: #94a3b8;
  text-align: center;
}
.db-side-msg.err { color: #fca5a5; }
.db-section { padding: 12px 0; }
.db-name {
  padding: 0 16px;
  font-size: 12px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: .05em;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.db-dot {
  width: 8px; height: 8px; border-radius: 50%;
}
.dot-ok { background: #10b981; box-shadow: 0 0 6px rgba(16,185,129,.4); }
.db-tbl-item {
  padding: 8px 16px;
  font-size: 13px;
  color: #e2e8f0;
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: background .15s, border-color .15s;
}
.db-tbl-item:hover { background: #334155; }
.db-tbl-item.active {
  background: #334155;
  border-left-color: #3b82f6;
  color: #60a5fa;
  font-weight: 600;
}

.db-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.db-placeholder {
  flex: 1; display: flex; align-items: center; justify-content: center;
  color: #64748b; font-size: 14px;
}
.db-toolbar {
  padding: 12px 20px;
  background: #1e293b;
  border-bottom: 1px solid #334155;
  display: flex;
  align-items: center;
  gap: 12px;
}
.db-table-title { font-weight: 600; font-size: 15px; color: #f8fafc; }
.db-total { font-size: 12px; color: #94a3b8; background: #0f172a; padding: 2px 8px; border-radius: 12px; }
.db-rows-msg { padding: 30px; text-align: center; color: #94a3b8; font-size: 14px; }
.db-rows-msg.err { color: #fca5a5; }

.db-table-wrap {
  flex: 1;
  overflow: auto;
  padding: 16px;
}
.db-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.db-th {
  background: #1e293b;
  color: #94a3b8;
  font-weight: 600;
  text-align: left;
  padding: 10px 12px;
  position: sticky;
  top: 0;
  z-index: 10;
  border-bottom: 2px solid #334155;
  white-space: nowrap;
}
.db-td {
  padding: 8px 12px;
  border-bottom: 1px solid #334155;
  color: #e2e8f0;
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.db-tr:hover .db-td {
  background: #1e293b;
}

.th-action, .td-action {
  width: 80px;
  text-align: center;
  position: sticky;
  right: 0;
  background: #0f172a;
}
.db-tr:hover .td-action { background: #1e293b; }
.db-th.th-action { background: #1e293b; z-index: 11; }

.row-btn {
  background: none; border: none; cursor: pointer; color: #94a3b8; margin: 0 4px; padding: 4px; transition: color .15s;
  line-height: 0;
}
.row-btn svg { width: 15px; height: 15px; }
.row-btn:hover { color: #60a5fa; }
.row-btn.del-btn:hover { color: #f87171; }

.modal-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,.6); z-index: 9999;
  display: flex; align-items: center; justify-content: center;
}
.modal-box {
  background: #1e293b; width: 440px; max-width: 90vw; border-radius: 12px;
  padding: 20px; border: 1px solid #334155; box-shadow: 0 10px 25px rgba(0,0,0,.5);
}
.modal-title { font-size: 16px; font-weight: 600; color: #f8fafc; margin-bottom: 16px; }
.modal-fields { display: flex; flex-direction: column; gap: 12px; max-height: 60vh; overflow-y: auto; margin-bottom: 16px; }
.field-row { display: flex; flex-direction: column; gap: 4px; }
.field-label { font-size: 12px; color: #94a3b8; }
.field-input { background: #0f172a; border: 1px solid #334155; color: #e2e8f0; padding: 8px; border-radius: 6px; outline: none; }
.field-input:focus { border-color: #3b82f6; }
.modal-err { color: #fca5a5; font-size: 13px; margin-bottom: 12px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; }
.db-btn { background: #334155; color: #e2e8f0; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; }
.db-btn:hover { background: #475569; }
.db-btn.primary { background: #3b82f6; color: #fff; }
.db-btn.primary:hover { background: #2563eb; }
</style>
