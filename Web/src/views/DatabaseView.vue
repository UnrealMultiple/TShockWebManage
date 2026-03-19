<template>
  <div class="db-root">

    <!-- 左侧：数据库 + 表列表 -->
    <aside class="db-sidebar">
      <div v-if="loadingDbs" class="db-side-msg">加载中…</div>
      <div v-else-if="dbsError" class="db-side-msg err">{{ dbsError }}</div>
      <template v-else>
        <div v-for="db in databases" :key="db.name" class="db-section">
          <div class="db-name">
            <span class="db-dot" :class="db.exists ? 'dot-ok' : 'dot-off'"></span>
            {{ db.name === 'auth' ? '认证数据库' : 'TShock 数据库' }}
            <span v-if="!db.exists" class="badge-off">不可用</span>
          </div>
          <template v-if="db.exists">
            <div v-if="loadingTables[db.name]" class="db-tbl-msg">加载中…</div>
            <div v-else-if="tablesError[db.name]" class="db-tbl-msg err">{{ tablesError[db.name] }}</div>
            <div
              v-for="tbl in (tables[db.name] || [])"
              :key="tbl"
              :class="['db-tbl-item', { active: activeDb === db.name && activeTable === tbl }]"
              @click="selectTable(db.name, tbl)"
            >{{ tbl }}</div>
          </template>
        </div>
      </template>
    </aside>

    <!-- 右侧：数据表格 -->
    <main class="db-main">
      <!-- 未选中表 -->
      <div v-if="!activeTable" class="db-placeholder">← 从左侧选择一个数据库表</div>

      <!-- 选中表 -->
      <template v-else>
        <div class="db-toolbar">
          <span class="db-table-title">{{ activeDb }} · {{ activeTable }}</span>
          <span class="db-total">共 {{ total }} 行</span>
          <div class="db-toolbar-actions">
            <button class="db-btn add-btn" @click="openInsert">＋ 新建行</button>
          </div>
        </div>

        <!-- 加载中 / 错误 -->
        <div v-if="loadingRows" class="db-rows-msg">加载中…</div>
        <div v-else-if="rowsError" class="db-rows-msg err">{{ rowsError }}</div>

        <!-- 表格 -->
        <div v-else class="db-table-wrap">
          <table class="db-table">
            <thead>
              <tr>
                <th v-for="col in columns" :key="col.name" class="db-th">
                  {{ col.name }}
                  <span v-if="col.pk" class="badge-pk">PK</span>
                  <span class="badge-type">{{ col.type || '?' }}</span>
                </th>
                <th class="db-th th-action">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in rows" :key="idx" class="db-tr">
                <td v-for="col in columns" :key="col.name" class="db-td">
                  <span class="db-cell">{{ row[col.name] }}</span>
                </td>
                <td class="db-td td-action">
                  <button class="row-btn edit-btn"  @click="openEdit(row)">✏</button>
                  <button class="row-btn del-btn"   @click="openDeleteRow(row)">🗑</button>
                </td>
              </tr>
              <tr v-if="rows.length === 0">
                <td :colspan="columns.length + 1" class="db-empty">（空表）</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 分页 -->
        <div v-if="!loadingRows && !rowsError" class="db-pagination">
          <button class="pg-btn" :disabled="page <= 1" @click="changePage(page - 1)">‹ 上一页</button>
          <span class="pg-info">第 {{ page }} / {{ totalPages }} 页</span>
          <button class="pg-btn" :disabled="page >= totalPages" @click="changePage(page + 1)">下一页 ›</button>
        </div>
      </template>
    </main>

    <!-- ── 编辑行 Modal ── -->
    <div v-if="editModal" class="modal-mask" @click.self="editModal = false">
      <div class="modal-box">
        <div class="modal-title">编辑行</div>
        <div class="modal-fields">
          <label v-for="col in columns" :key="col.name" class="field-row">
            <span class="field-label">
              {{ col.name }}
              <span v-if="col.pk" class="badge-pk">PK</span>
            </span>
            <input
              v-model="editForm[col.name]"
              :disabled="col.pk"
              class="field-input"
              :class="{ disabled: col.pk }"
              :placeholder="col.type"
            />
          </label>
        </div>
        <div v-if="editError" class="modal-err">{{ editError }}</div>
        <div class="modal-actions">
          <button class="db-btn cancel-btn" @click="editModal = false">取消</button>
          <button class="db-btn save-btn" :disabled="editBusy" @click="submitEdit">
            {{ editBusy ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── 新建行 Modal ── -->
    <div v-if="insertModal" class="modal-mask" @click.self="insertModal = false">
      <div class="modal-box">
        <div class="modal-title">新建行</div>
        <div class="modal-fields">
          <label v-for="col in nonPkColumns" :key="col.name" class="field-row">
            <span class="field-label">{{ col.name }}</span>
            <input
              v-model="insertForm[col.name]"
              class="field-input"
              :placeholder="col.type"
            />
          </label>
        </div>
        <div v-if="insertError" class="modal-err">{{ insertError }}</div>
        <div class="modal-actions">
          <button class="db-btn cancel-btn" @click="insertModal = false">取消</button>
          <button class="db-btn save-btn" :disabled="insertBusy" @click="submitInsert">
            {{ insertBusy ? '插入中…' : '插入' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── 删除行确认 Modal ── -->
    <div v-if="deleteRowModal" class="modal-mask" @click.self="deleteRowModal = false">
      <div class="modal-box">
        <div class="modal-title">确认删除</div>
        <div class="modal-body-text">
          删除 <strong>{{ activeTable }}</strong> 中
          <strong>{{ pkCol }} = {{ deleteRowTarget?.[pkCol] }}</strong> 的记录？此操作不可撤销。
        </div>
        <div v-if="deleteRowError" class="modal-err">{{ deleteRowError }}</div>
        <div class="modal-actions">
          <button class="db-btn cancel-btn" @click="deleteRowModal = false">取消</button>
          <button class="db-btn danger-btn" :disabled="deleteRowBusy" @click="submitDeleteRow">
            {{ deleteRowBusy ? '删除中…' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { listDatabases, listTables, queryTable, updateRow, insertRow, deleteRow } from '@/api/database'

// ── 数据库 + 表列表 ───────────────────────────────────────────
const databases     = ref([])
const loadingDbs    = ref(false)
const dbsError      = ref('')
const tables        = ref({})       // { dbName: [tableName, ...] }
const loadingTables = ref({})
const tablesError   = ref({})

async function fetchDatabases() {
  loadingDbs.value = true
  dbsError.value   = ''
  try {
    const res = await listDatabases()
    databases.value = res.data
    for (const db of res.data) {
      if (db.exists) fetchTables(db.name)
    }
  } catch (e) {
    dbsError.value = e.message
  } finally {
    loadingDbs.value = false
  }
}

async function fetchTables(dbName) {
  loadingTables.value = { ...loadingTables.value, [dbName]: true }
  tablesError.value   = { ...tablesError.value,   [dbName]: '' }
  try {
    const res = await listTables(dbName)
    tables.value = { ...tables.value, [dbName]: res.data }
  } catch (e) {
    tablesError.value = { ...tablesError.value, [dbName]: e.message }
  } finally {
    loadingTables.value = { ...loadingTables.value, [dbName]: false }
  }
}

onMounted(fetchDatabases)

// ── 当前表 ────────────────────────────────────────────────────
const activeDb    = ref('')
const activeTable = ref('')
const columns     = ref([])
const rows        = ref([])
const total       = ref(0)
const page        = ref(1)
const pageSize    = ref(50)
const loadingRows = ref(false)
const rowsError   = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const pkCol      = computed(() => columns.value.find(c => c.pk)?.name || columns.value[0]?.name)
const nonPkColumns = computed(() => columns.value.filter(c => !c.pk))

async function selectTable(dbName, tableName) {
  activeDb.value    = dbName
  activeTable.value = tableName
  page.value        = 1
  await loadRows()
}

async function loadRows() {
  loadingRows.value = true
  rowsError.value   = ''
  try {
    const res = await queryTable(activeDb.value, activeTable.value, page.value, pageSize.value)
    columns.value = res.data.columns
    rows.value    = res.data.rows
    total.value   = res.data.total
  } catch (e) {
    rowsError.value = e.message
  } finally {
    loadingRows.value = false
  }
}

async function changePage(p) {
  page.value = p
  await loadRows()
}

// ── 编辑行 ────────────────────────────────────────────────────
const editModal  = ref(false)
const editForm   = ref({})
const editBusy   = ref(false)
const editError  = ref('')

function openEdit(row) {
  editForm.value  = { ...row }
  editError.value = ''
  editBusy.value  = false
  editModal.value = true
}

async function submitEdit() {
  editError.value = ''
  editBusy.value  = true
  const pk   = pkCol.value
  const pkV  = editForm.value[pk]
  // 只发送非 PK 列
  const data = {}
  for (const col of columns.value) {
    if (!col.pk) data[col.name] = editForm.value[col.name]
  }
  try {
    await updateRow(activeDb.value, activeTable.value, pk, pkV, data)
    editModal.value = false
    await loadRows()
  } catch (e) {
    editError.value = e.message
  } finally {
    editBusy.value = false
  }
}

// ── 新建行 ────────────────────────────────────────────────────
const insertModal  = ref(false)
const insertForm   = ref({})
const insertBusy   = ref(false)
const insertError  = ref('')

function openInsert() {
  const form = {}
  for (const col of nonPkColumns.value) form[col.name] = ''
  insertForm.value  = form
  insertError.value = ''
  insertBusy.value  = false
  insertModal.value = true
}

async function submitInsert() {
  insertError.value = ''
  insertBusy.value  = true
  try {
    await insertRow(activeDb.value, activeTable.value, insertForm.value)
    insertModal.value = false
    await loadRows()
  } catch (e) {
    insertError.value = e.message
  } finally {
    insertBusy.value = false
  }
}

// ── 删除行 ────────────────────────────────────────────────────
const deleteRowModal  = ref(false)
const deleteRowTarget = ref(null)
const deleteRowBusy   = ref(false)
const deleteRowError  = ref('')

function openDeleteRow(row) {
  deleteRowTarget.value = row
  deleteRowError.value  = ''
  deleteRowBusy.value   = false
  deleteRowModal.value  = true
}

async function submitDeleteRow() {
  deleteRowError.value = ''
  deleteRowBusy.value  = true
  const pk  = pkCol.value
  const pkV = deleteRowTarget.value[pk]
  try {
    await deleteRow(activeDb.value, activeTable.value, pk, pkV)
    deleteRowModal.value = false
    if (rows.value.length === 1 && page.value > 1) page.value--
    await loadRows()
  } catch (e) {
    deleteRowError.value = e.message
  } finally {
    deleteRowBusy.value = false
  }
}
</script>

<style scoped>
/* ── 布局 ── */
.db-root {
  display: flex;
  height: 100%;
  min-height: 0;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 13px;
  overflow: hidden;
}

/* ── 左侧边栏 ── */
.db-sidebar {
  width: 220px;
  min-width: 160px;
  flex-shrink: 0;
  background: #1e293b;
  border-right: 1px solid #334155;
  overflow-y: auto;
  padding: 12px 0;
}

.db-section { margin-bottom: 8px; }

.db-name {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px 4px;
  font-weight: 700;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: .04em;
  color: #94a3b8;
}

.db-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-ok  { background: #22c55e; }
.dot-off { background: #475569; }

.badge-off {
  margin-left: auto;
  font-size: 10px; font-weight: 600;
  background: #334155; color: #64748b;
  border-radius: 4px; padding: 1px 5px;
}

.db-tbl-item {
  padding: 5px 14px 5px 26px;
  cursor: pointer;
  border-radius: 0;
  color: #94a3b8;
  transition: background .1s, color .1s;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.db-tbl-item:hover  { background: #334155; color: #e2e8f0; }
.db-tbl-item.active { background: #1d4ed8; color: #fff; font-weight: 600; }

.db-side-msg, .db-tbl-msg {
  padding: 8px 14px;
  color: #64748b;
  font-size: 12px;
}
.db-side-msg.err, .db-tbl-msg.err { color: #f87171; }

/* ── 主区域 ── */
.db-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.db-placeholder {
  margin: auto;
  color: #475569;
  font-size: 14px;
}

/* ── 工具栏 ── */
.db-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 18px;
  border-bottom: 1px solid #1e293b;
  background: #0f172a;
  flex-shrink: 0;
}

.db-table-title {
  font-weight: 700;
  font-size: 14px;
  color: #f1f5f9;
}

.db-total {
  font-size: 12px;
  color: #64748b;
}

.db-toolbar-actions { margin-left: auto; }

.db-btn {
  padding: 5px 14px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid;
  transition: all .12s;
}
.add-btn    { background: #16a34a; color: #fff; border-color: #15803d; }
.add-btn:hover { background: #15803d; }
.save-btn   { background: #2563eb; color: #fff; border-color: #1d4ed8; }
.save-btn:hover:not(:disabled) { background: #1d4ed8; }
.cancel-btn { background: #334155; color: #94a3b8; border-color: #475569; }
.cancel-btn:hover { background: #475569; color: #e2e8f0; }
.danger-btn { background: #dc2626; color: #fff; border-color: #b91c1c; }
.danger-btn:hover:not(:disabled) { background: #b91c1c; }
.db-btn:disabled { opacity: .5; cursor: not-allowed; }

/* ── 表格 ── */
.db-table-wrap {
  flex: 1;
  overflow: auto;
  padding: 0 12px;
}

.db-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}

.db-th {
  position: sticky;
  top: 0;
  background: #1e293b;
  color: #94a3b8;
  font-weight: 600;
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid #334155;
  white-space: nowrap;
}
.th-action { width: 80px; text-align: center; }

.db-tr:nth-child(even) { background: #0f1f35; }
.db-tr:hover           { background: #1e2f4a; }

.db-td {
  padding: 6px 10px;
  border-bottom: 1px solid #1e293b;
  vertical-align: top;
  max-width: 280px;
}
.td-action { text-align: center; white-space: nowrap; }

.db-cell {
  display: block;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #cbd5e1;
}

.db-empty {
  text-align: center;
  padding: 24px;
  color: #475569;
}

.badge-pk {
  margin-left: 4px;
  font-size: 10px;
  font-weight: 700;
  background: #1d4ed8;
  color: #bfdbfe;
  border-radius: 3px;
  padding: 1px 4px;
}
.badge-type {
  margin-left: 4px;
  font-size: 10px;
  font-weight: 500;
  background: #334155;
  color: #64748b;
  border-radius: 3px;
  padding: 1px 4px;
}

/* ── 行操作按钮 ── */
.row-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 5px;
  border-radius: 4px;
  transition: background .1s;
}
.edit-btn:hover { background: #1e3a5f; }
.del-btn:hover  { background: #4c1d1d; }

/* ── 分页 ── */
.db-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 10px;
  border-top: 1px solid #1e293b;
  flex-shrink: 0;
}
.pg-btn {
  padding: 4px 14px;
  border-radius: 6px;
  background: #1e293b;
  color: #94a3b8;
  border: 1px solid #334155;
  cursor: pointer;
  font-size: 12px;
  transition: all .12s;
}
.pg-btn:hover:not(:disabled) { background: #334155; color: #e2e8f0; }
.pg-btn:disabled { opacity: .4; cursor: not-allowed; }
.pg-info { font-size: 12px; color: #64748b; }

/* ── 加载 / 错误 ── */
.db-rows-msg { padding: 24px; color: #64748b; text-align: center; }
.db-rows-msg.err { color: #f87171; }

/* ── Modals ── */
.modal-mask {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.55);
  display: flex; align-items: center; justify-content: center;
  z-index: 300;
}
.modal-box {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 24px 28px;
  width: 420px;
  max-width: 95vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.modal-title {
  font-size: 15px;
  font-weight: 700;
  color: #f1f5f9;
}
.modal-body-text {
  font-size: 13px;
  color: #94a3b8;
  line-height: 1.6;
}
.modal-fields {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  max-height: 50vh;
  padding-right: 4px;
}
.field-row {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.field-label {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: .03em;
}
.field-input {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 6px 10px;
  color: #e2e8f0;
  font-size: 13px;
  outline: none;
  transition: border-color .12s;
}
.field-input:focus { border-color: #2563eb; }
.field-input.disabled { opacity: .5; cursor: not-allowed; }

.modal-err {
  background: #450a0a;
  color: #fca5a5;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
