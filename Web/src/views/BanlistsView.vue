<template>
  <div class="bl-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="page-header-left">
        <h1 class="page-title">图格/物品/弹幕封禁管理</h1>
        <span class="page-subtitle">TShock 图格·物品·弹幕黑名单</span>
      </div>
      <div class="page-header-right">
        <button class="btn btn-sm btn-outline" @click="loadData" :disabled="loading || !agentOnline || !activeServerKey">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0">
            <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
          </svg>
          {{ loading ? '加载中…' : '刷新' }}
        </button>
        <button class="btn btn-sm btn-outline" @click="doReload" :disabled="!agentOnline || !activeServerKey || reloading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0">
            <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-.49-3.18"/>
          </svg>
          {{ reloading ? '重载中…' : '立即重载' }}
        </button>
        <button class="btn btn-sm btn-primary" @click="doSave" :disabled="!agentOnline || !activeServerKey || saving">
          <svg v-if="saving" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0;animation:spin .8s linear infinite">
            <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
          </svg>
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </div>
    </div>

    <div class="bl-body">

      <!-- Agent 离线 -->
      <div v-if="!agentOnline" class="state-box state-offline">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <span>Agent 未连接，无法管理封禁列表。请先启动服务器。</span>
      </div>

      <!-- 无服务器 -->
      <div v-else-if="!activeServerKey" class="state-box state-empty">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/>
          <line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/>
        </svg>
        <p>请先在左侧选择一个服务器</p>
      </div>

      <!-- 加载中 -->
      <div v-else-if="loading" class="state-box state-loading">
        <div class="spinner"></div>
        <span>正在加载封禁数据…</span>
      </div>

      <!-- 错误 -->
      <div v-else-if="loadError" class="state-box state-error">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <div>
          <strong>加载失败</strong><p>{{ loadError }}</p>
          <button class="btn btn-sm btn-outline" style="margin-top:8px" @click="loadData">重试</button>
        </div>
      </div>

      <template v-else>
        <!-- Toast -->
        <div v-if="toast" :class="['toast', toast.ok ? 'toast-ok' : 'toast-err']">
          {{ toast.msg }}
          <button class="toast-close" @click="toast = null">✕</button>
        </div>

        <!-- 工具栏 -->
        <div class="body-toolbar">
          <button class="btn btn-sm btn-primary" @click="openCreate" :disabled="!agentOnline || !activeServerKey">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:13px;height:13px;flex-shrink:0">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            新增封禁
          </button>
        </div>

        <!-- 类型标签页 -->
        <div class="tabs">
          <button :class="['tab', { active: activeTab === 'tile' }]"   @click="activeTab = 'tile'">
            图格封禁 <span class="tab-count">{{ tileItems.length }}</span>
          </button>
          <button :class="['tab', { active: activeTab === 'item' }]"   @click="activeTab = 'item'">
            物品封禁 <span class="tab-count">{{ itemItems.length }}</span>
          </button>
          <button :class="['tab', { active: activeTab === 'proj' }]"   @click="activeTab = 'proj'">
            弹幕封禁 <span class="tab-count">{{ projItems.length }}</span>
          </button>
        </div>

        <!-- 搜索栏 -->
        <div class="search-bar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input v-model="searchQuery" class="search-input" :placeholder="'搜索 ' + tabLabel + ' ID 或名称…'" />
          <button v-if="searchQuery" class="search-clear" @click="searchQuery = ''">✕</button>
        </div>

        <!-- 封禁列表 -->
        <div class="bl-table-wrap">
          <table class="bl-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>名称</th>
                <th>封禁原因</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!pagedItems.length">
                <td colspan="4" class="empty-row">
                  {{ searchQuery ? '没有符合搜索条件的记录' : '暂无 ' + tabLabel + ' 封禁记录' }}
                </td>
              </tr>
              <tr v-for="item in pagedItems" :key="item.id">
                <td><span class="item-id">{{ item.id }}</span></td>
                <td>{{ item.name || '—' }}</td>
                <td class="ban-reason">{{ item.reason || '—' }}</td>
                <td>
                  <button class="btn btn-xs btn-danger" @click="confirmRemove(item)" :disabled="submitting">移除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 分页 -->
        <div v-if="filteredItems.length > pageSize" class="pagination">
          <button class="btn btn-xs btn-outline" :disabled="page <= 1" @click="page--">上一页</button>
          <span class="page-info">第 {{ page }} 页 / 共 {{ totalPages }} 页（{{ filteredItems.length }} 条）</span>
          <button class="btn btn-xs btn-outline" :disabled="page >= totalPages" @click="page++">下一页</button>
        </div>
      </template>
    </div>

    <!-- ── 新增封禁模态框 ── -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-box">
        <div class="modal-header">
          <h3>新增 {{ tabLabel }} 封禁</h3>
          <button class="modal-close" @click="closeModal">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-field">
            <label class="form-label">类型</label>
            <div class="type-selector">
              <button :class="['type-btn', { active: form.type === 'tile' }]" @click="form.type = 'tile'">图格</button>
              <button :class="['type-btn', { active: form.type === 'item' }]" @click="form.type = 'item'">物品</button>
              <button :class="['type-btn', { active: form.type === 'proj' }]" @click="form.type = 'proj'">弹幕</button>
            </div>
          </div>
          <div class="form-field">
            <label class="form-label">ID <span class="required">*</span></label>
            <input v-model.number="form.id" type="number" class="form-input" placeholder="游戏内数字 ID" min="0" />
          </div>
          <div class="form-field">
            <label class="form-label">封禁原因</label>
            <input v-model="form.reason" class="form-input" placeholder="（可选）" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="closeModal">取消</button>
          <button class="btn btn-danger" @click="submitAdd" :disabled="submitting || form.id === null || form.id === ''">
            {{ submitting ? '添加中…' : '确认添加' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── 移除确认模态框 ── -->
    <div v-if="removeTarget" class="modal-overlay" @click.self="removeTarget = null">
      <div class="modal-box modal-box-sm">
        <div class="modal-header">
          <h3>确认移除封禁</h3>
          <button class="modal-close" @click="removeTarget = null">✕</button>
        </div>
        <div class="modal-body">
          <p>确定要移除 ID 为 <strong>{{ removeTarget.id }}</strong>（{{ removeTarget.name || '未知名称' }}）的 {{ tabLabel }} 封禁吗？</p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="removeTarget = null">取消</button>
          <button class="btn btn-primary" @click="doRemove" :disabled="submitting">
            {{ submitting ? '处理中…' : '确认移除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, inject, watch } from 'vue'

const props = defineProps({
  agentOnline: { type: Boolean, default: false },
})

const activeServerKey = inject('activeServerKey', ref(''))

const loading      = ref(false)
const loadError    = ref('')
const tileItems    = ref([])
const itemItems    = ref([])
const projItems    = ref([])
const toast        = ref(null)
const showModal    = ref(false)
const removeTarget = ref(null)
const submitting   = ref(false)
const reloading    = ref(false)
const saving       = ref(false)
const activeTab    = ref('tile')
const searchQuery  = ref('')
const page         = ref(1)
const pageSize     = 30

const form = ref({ type: 'tile', id: '', reason: '' })

const tabLabel = computed(() => ({ tile: '图格', item: '物品', proj: '弹幕' }[activeTab.value] || '')  )

const currentItems = computed(() => {
  if (activeTab.value === 'tile') return tileItems.value
  if (activeTab.value === 'item') return itemItems.value
  return projItems.value
})

const filteredItems = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return currentItems.value
  return currentItems.value.filter(i =>
    String(i.id).includes(q) || (i.name || '').toLowerCase().includes(q)
  )
})

const totalPages = computed(() => Math.ceil(filteredItems.value.length / pageSize))
const pagedItems = computed(() => {
  const start = (page.value - 1) * pageSize
  return filteredItems.value.slice(start, start + pageSize)
})

// ── 加载数据 ───────────────────────────────────────────────────────
function loadData() {
  if (!activeServerKey.value) return
  loading.value   = true
  loadError.value = ''
  window.__tshockSend?.({
    type: 'list_banlists',
    msg_id: `bl-list-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

function openCreate() {
  form.value = { type: activeTab.value, id: '', reason: '' }
  showModal.value = true
}
function closeModal() { showModal.value = false }

function submitAdd() {
  if (form.value.id === '' || form.value.id === null) return
  submitting.value = true
  window.__tshockSend?.({
    type: 'add_banlist',
    msg_id: `bl-add-${Date.now()}`,
    timestamp: Date.now(),
    payload: {
      agent_key: activeServerKey.value,
      ban_type: form.value.type,
      id: Number(form.value.id),
      reason: form.value.reason.trim(),
    },
  })
}

function confirmRemove(item) { removeTarget.value = item }

function doRemove() {
  if (!removeTarget.value) return
  submitting.value = true
  window.__tshockSend?.({
    type: 'remove_banlist',
    msg_id: `bl-del-${Date.now()}`,
    timestamp: Date.now(),
    payload: {
      agent_key: activeServerKey.value,
      ban_type: activeTab.value,
      id: removeTarget.value.id,
    },
  })
}

function showToast(ok, msg) {
  toast.value = { ok, msg }
  setTimeout(() => { toast.value = null }, 4000)
}

function doReload() {
  if (!activeServerKey.value) return
  reloading.value = true
  window.__tshockSend?.({
    type: 'reload_tshock',
    msg_id: `bl-reload-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

function doSave() {
  if (!activeServerKey.value) return
  saving.value = true
  window.__tshockSend?.({
    type: 'save_world',
    msg_id: `bl-save-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

// ── WS 消息处理 ────────────────────────────────────────────────────
function onWsMessage(e) {
  const pkt = e.detail
  const p   = pkt.payload || {}

  if (pkt.type === 'list_banlists_resp') {
    loading.value = false
    if (p.success) {
      tileItems.value = p.tiles || []
      itemItems.value = p.items || []
      projItems.value = p.projectiles || []
      page.value = 1
    } else {
      loadError.value = p.msg || '加载失败'
    }
    return
  }

  if (pkt.type === 'add_banlist_resp') {
    submitting.value = false
    showToast(p.success ?? false, p.msg || (p.success ? '添加成功' : '添加失败'))
    if (p.success) { closeModal(); loadData() }
    return
  }

  if (pkt.type === 'remove_banlist_resp') {
    submitting.value = false
    showToast(p.success ?? false, p.msg || (p.success ? '已移除' : '移除失败'))
    if (p.success) { removeTarget.value = null; loadData() }
    return
  }

  if (pkt.type === 'reload_tshock_resp') {
    reloading.value = false
    showToast(p.success ?? false, p.msg || (p.success ? '重载成功' : '重载失败'))
    return
  }

  if (pkt.type === 'save_world_resp') {
    saving.value = false
    showToast(p.success ?? false, p.msg || (p.success ? '保存成功' : '保存失败'))
    return
  }
}

onMounted(() => {
  window.addEventListener('ws-message', onWsMessage)
  if (props.agentOnline && activeServerKey.value) loadData()
})
onUnmounted(() => {
  window.removeEventListener('ws-message', onWsMessage)
})

watch([activeServerKey, () => props.agentOnline], ([key, online]) => {
  if (key && online) loadData()
  searchQuery.value = ''
  page.value = 1
})

watch(activeTab, () => {
  searchQuery.value = ''
  page.value = 1
  form.value.type = activeTab.value
})
</script>

<style scoped>
.bl-page { display: flex; flex-direction: column; height: 100%; overflow: hidden; background: #f8fafc; }

/* ── 页头 ───────────────────────────────────────────────────────── */
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 28px 16px; background: #fff; border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0; flex-wrap: wrap; gap: 12px;
}
.page-header-left { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.page-header-right { display: flex; gap: 8px; }
.page-title { margin: 0; font-size: 18px; font-weight: 700; color: #0f172a; }
.page-subtitle {
  font-size: 12px; color: #64748b;
  background: #f1f5f9; border: 1px solid #e2e8f0;
  padding: 2px 8px; border-radius: 20px; font-family: monospace;
}

/* ── 主体 ────────────────────────────────────────────────────────── */
.bl-body { flex: 1; overflow-y: auto; padding: 24px 28px; box-sizing: border-box; }
.body-toolbar { display: flex; justify-content: flex-end; margin-bottom: 14px; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 状态框 ──────────────────────────────────────────────────────── */
.state-box { display: flex; align-items: center; gap: 12px; padding: 20px 24px; border-radius: 10px; font-size: 14px; margin-bottom: 16px; }
.state-box svg { width: 20px; height: 20px; flex-shrink: 0; }
.state-offline { background: #fff7ed; color: #92400e; border: 1px solid #fed7aa; }
.state-offline svg { stroke: #f97316; }
.state-empty { background: #f8fafc; color: #94a3b8; border: 1px solid #e2e8f0; justify-content: center; flex-direction: column; padding: 60px 24px; text-align: center; }
.state-empty svg { width: 40px; height: 40px; stroke: #cbd5e1; margin-bottom: 8px; }
.state-loading { background: #f8fafc; color: #64748b; justify-content: center; padding: 60px 24px; flex-direction: row; gap: 12px; }
.state-error { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.state-error svg { stroke: #ef4444; }
.spinner { width: 28px; height: 28px; border: 3px solid #e2e8f0; border-top-color: #3b82f6; border-radius: 50%; animation: spin .7s linear infinite; flex-shrink: 0; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 标签页 ──────────────────────────────────────────────────────── */
.tabs { display: flex; gap: 4px; margin-bottom: 16px; background: #f1f5f9; padding: 4px; border-radius: 8px; width: fit-content; }
.tab { padding: 6px 16px; border: none; border-radius: 6px; background: transparent; color: #64748b; font-size: 13px; font-weight: 500; cursor: pointer; transition: .15s; display: flex; align-items: center; gap: 6px; }
.tab.active { background: #fff; color: #0f172a; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.tab-count { font-size: 11px; font-weight: 600; background: #e2e8f0; color: #64748b; padding: 1px 6px; border-radius: 10px; }
.tab.active .tab-count { background: #e0e7ff; color: #4f46e5; }

/* ── 搜索栏 ───────────────────────────────────────────────────────── */
.search-bar { display: flex; align-items: center; gap: 8px; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 12px; margin-bottom: 16px; }
.search-bar svg { width: 16px; height: 16px; stroke: #94a3b8; flex-shrink: 0; }
.search-input { flex: 1; border: none; outline: none; font-size: 14px; color: #0f172a; background: transparent; }
.search-clear { background: none; border: none; cursor: pointer; color: #94a3b8; font-size: 14px; padding: 0; }
.search-clear:hover { color: #475569; }

/* ── 表格 ────────────────────────────────────────────────────────── */
.bl-table-wrap { overflow-x: auto; }
.bl-table { width: 100%; border-collapse: collapse; font-size: 14px; background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; }
.bl-table th { background: #f8fafc; padding: 10px 14px; text-align: left; font-size: 12px; font-weight: 600; color: #64748b; border-bottom: 1px solid #e2e8f0; }
.bl-table td { padding: 11px 14px; border-bottom: 1px solid #f1f5f9; color: #334155; vertical-align: middle; }
.bl-table tr:last-child td { border-bottom: none; }
.item-id { font-family: monospace; font-size: 13px; font-weight: 600; color: #4f46e5; background: #eff6ff; padding: 2px 8px; border-radius: 4px; }
.ban-reason { color: #64748b; font-size: 13px; }
.empty-row { text-align: center; color: #94a3b8; padding: 40px; }

/* ── 分页 ────────────────────────────────────────────────────────── */
.pagination { display: flex; align-items: center; gap: 12px; margin-top: 16px; justify-content: center; }
.page-info { font-size: 13px; color: #64748b; }

/* ── Toast ───────────────────────────────────────────────────────── */
.toast { display: flex; align-items: center; padding: 10px 16px; border-radius: 8px; font-size: 14px; margin-bottom: 16px; gap: 12px; }
.toast-ok  { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.toast-err { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
.toast-close { background: none; border: none; cursor: pointer; font-size: 14px; color: inherit; padding: 0; margin-left: auto; }

/* ── 按钮 ────────────────────────────────────────────────────────── */
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 7px 16px; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; border: none; transition: all 0.15s; }
.btn svg { width: 14px; height: 14px; flex-shrink: 0; }
.btn:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-sm  { padding: 7px 16px; }
.btn-xs  { padding: 4px 10px; font-size: 12px; border-radius: 6px; }
.btn-primary { background: #3b82f6; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-outline { background: #fff; color: #374151; border: 1px solid #d1d5db; }
.btn-outline:hover:not(:disabled) { background: #f9fafb; border-color: #9ca3af; }
.btn-danger { background: #ef4444; color: #fff; }
.btn-danger:hover:not(:disabled) { background: #dc2626; }

/* ── 模态框 ───────────────────────────────────────────────────────── */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.3); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-box { background: #fff; border-radius: 12px; width: 460px; max-width: 95vw; box-shadow: 0 20px 60px rgba(0,0,0,.18); display: flex; flex-direction: column; max-height: 90vh; }
.modal-box-sm { width: 400px; }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 18px 22px 14px; border-bottom: 1px solid #e2e8f0; }
.modal-header h3 { margin: 0; font-size: 16px; font-weight: 700; color: #0f172a; }
.modal-close { background: none; border: none; font-size: 18px; cursor: pointer; color: #94a3b8; padding: 0; }
.modal-close:hover { color: #0f172a; }
.modal-body { padding: 20px 22px; overflow-y: auto; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; padding: 14px 22px; border-top: 1px solid #e2e8f0; }
.form-field { margin-bottom: 16px; }
.form-label { display: block; font-size: 13px; font-weight: 500; color: #374151; margin-bottom: 6px; }
.required { color: #ef4444; }
.form-input { width: 100%; box-sizing: border-box; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; color: #0f172a; outline: none; transition: border-color .15s; }
.form-input:focus { border-color: #6366f1; box-shadow: 0 0 0 2px rgba(99,102,241,.1); }
.type-selector { display: flex; gap: 8px; }
.type-btn { padding: 6px 16px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; color: #64748b; font-size: 13px; cursor: pointer; transition: .15s; }
.type-btn.active { background: #eff6ff; border-color: #6366f1; color: #4f46e5; font-weight: 600; }
</style>
