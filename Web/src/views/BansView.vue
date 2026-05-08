<template>
  <div class="bans-page">
    <PageHeader title="用户封禁管理" subtitle="TShock Ban Ticket 管理" heading-tag="h1">
      <template #actions>
        <button class="cfg-btn cfg-btn-outline" @click="loadBans" :disabled="loading || !agentOnline || !activeServerKey">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/></svg>
          {{ loading ? '加载中…' : '刷新列表' }}
        </button>
        <button class="cfg-btn cfg-btn-primary" @click="openBanModal" :disabled="!agentOnline || !activeServerKey">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          新建封禁
        </button>
      </template>
    </PageHeader>

    <AgentOfflineNotice v-if="!agentOnline" message="Agent 未连接，无法管理封禁。请先启动服务器。" />

    <div v-else class="bans-body">
      <div v-if="!activeServerKey" class="state-box state-empty">
        <p>请先在左侧选择一个服务器</p>
      </div>

      <div v-else-if="loading" class="state-box state-loading">
        <div class="spinner"></div>
        <span>正在加载封禁列表...</span>
      </div>

      <AgentOfflineNotice v-else-if="loadError" type="error" :message="loadError" show-retry @retry="loadBans" />

      <template v-else>
        <div v-if="toast" :class="['toast', toast.ok ? 'toast-ok' : 'toast-err']">
          {{ toast.msg }}
          <button class="toast-close" @click="toast = null">x</button>
        </div>

        <div class="toolbar">
          <div class="filter-tabs">
            <button :class="['tab', { active: statusFilter === 'active' }]" @click="statusFilter = 'active'">
              生效中
            </button>
            <button :class="['tab', { active: statusFilter === 'all' }]" @click="statusFilter = 'all'">
              全部
            </button>
          </div>

          <div class="search-wrap">
            <input
              v-model.trim="searchQuery"
              class="search-input"
              placeholder="搜索 Ticket / 玩家 / 标识 / 原因..."
            />
          </div>
        </div>

        <div class="table-wrap">
          <table class="ban-table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>玩家/UUID/IP</th>
                <th>原因</th>
                <th>操作人员</th>
                <th>封禁时间</th>
                <th>到期时间</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!pagedBans.length">
                <td colspan="8" class="empty-row">
                  {{ searchQuery ? '没有符合搜索条件的封禁记录' : '暂无封禁记录' }}
                </td>
              </tr>
              <tr v-for="row in pagedBans" :key="row.ticket">
                <td>
                  <span class="ticket-tag">#{{ row.ticket }}</span>
                </td>
                <td class="mono">{{ row.identifier || '-' }}</td>
                <td>{{ row.reason || '-' }}</td>
                <td>{{ row.banned_by || '-' }}</td>
                <td class="mono">{{ row.ban_time || '-' }}</td>
                <td class="mono">{{ row.expiration_time || '永久' }}</td>
                <td>
                  <span :class="['status-pill', row.active ? 'status-active' : 'status-expired']">
                    {{ row.active ? '生效中' : '已过期' }}
                  </span>
                  <span v-if="row.active && row.remaining_seconds !== null" class="status-subtext">
                    剩余 {{ formatRemaining(row.remaining_seconds) }}
                  </span>
                </td>
                <td>
                  <button
                    class="btn btn-xs btn-outline"
                    :disabled="submitting"
                    @click="openEditExpireModal(row)"
                  >
                    改到期
                  </button>
                  <button
                    class="btn btn-xs btn-danger"
                    :disabled="submitting || !row.active"
                    @click="confirmUnban(row)"
                  >
                    解封
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="filteredBans.length > pageSize" class="pagination">
          <button class="btn btn-xs btn-outline" :disabled="page <= 1" @click="page--">上一页</button>
          <span class="page-info">第 {{ page }} 页 / 共 {{ totalPages }} 页（{{ filteredBans.length }} 条）</span>
          <button class="btn btn-xs btn-outline" :disabled="page >= totalPages" @click="page++">下一页</button>
        </div>
      </template>
    </div>

    <div v-if="showBanModal" class="modal-overlay" @click.self="closeBanModal">
      <div class="modal-box">
        <div class="modal-header">
          <h3>新建用户封禁</h3>
          <button class="modal-close" @click="closeBanModal">x</button>
        </div>
        <div class="modal-body">
          <div class="form-field">
            <label class="form-label">玩家名 / 账号名 <span class="required">*</span></label>
            <input v-model.trim="banForm.player" class="form-input" placeholder="例如：Steve" />
          </div>
          <div class="form-field">
            <label class="form-label">封禁时长</label>
            <input v-model.trim="banForm.duration" class="form-input" placeholder="格式 10d0m0s，留空为永久" />
          </div>
          <div class="form-field">
            <label class="form-label">封禁原因</label>
            <input v-model.trim="banForm.reason" class="form-input" placeholder="例如：恶意破坏" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="closeBanModal">取消</button>
          <button class="btn btn-danger" :disabled="submitting || !banForm.player" @click="submitBan">
            {{ submitting ? '提交中...' : '确认封禁' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="unbanTarget" class="modal-overlay" @click.self="unbanTarget = null">
      <div class="modal-box modal-box-sm">
        <div class="modal-header">
          <h3>确认解封</h3>
          <button class="modal-close" @click="unbanTarget = null">x</button>
        </div>
        <div class="modal-body">
          <p>确定要解除 Ticket <strong>#{{ unbanTarget.ticket }}</strong> 的封禁吗？</p>
          <p class="confirm-sub">对象：{{ unbanTarget.target || unbanTarget.identifier || '-' }}</p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="unbanTarget = null">取消</button>
          <button class="btn btn-primary" :disabled="submitting" @click="submitUnban">
            {{ submitting ? '处理中...' : '确认解封' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="editExpireTarget" class="modal-overlay" @click.self="editExpireTarget = null">
      <div class="modal-box modal-box-sm">
        <div class="modal-header">
          <h3>修改到期时间</h3>
          <button class="modal-close" @click="editExpireTarget = null">x</button>
        </div>
        <div class="modal-body">
          <p>Ticket：<strong>#{{ editExpireTarget.ticket }}</strong></p>
          <p class="confirm-sub">标识：{{ editExpireTarget.identifier || '-' }}</p>
          <div class="form-field" style="margin-top: 12px;">
            <label class="form-label">到期时间</label>
            <input
              v-model="expireForm.datetime"
              class="form-input"
              type="datetime-local"
              :disabled="expireForm.permanent"
            />
          </div>
          <label class="check-row">
            <input v-model="expireForm.permanent" type="checkbox" />
            设为永久封禁
          </label>
          <p class="confirm-sub">不勾选永久时，请选择具体日期时间。</p>
          <p class="confirm-sub">保存后封禁 Ticket 可能会重建为新编号。</p>
          <div v-if="expireFormError" class="form-error">{{ expireFormError }}</div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="editExpireTarget = null">取消</button>
          <button class="btn btn-primary" :disabled="submitting" @click="submitUpdateExpire">
            {{ submitting ? '处理中...' : '确认修改' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, onMounted, onUnmounted, ref, watch } from 'vue'
import AgentOfflineNotice from '@/components/AgentOfflineNotice.vue'
import PageHeader from '@/components/PageHeader.vue'

const props = defineProps({
  agentOnline: { type: Boolean, default: false },
})

const activeServerKey = inject('activeServerKey', ref(''))

const loading = ref(false)
const loadError = ref('')
const submitting = ref(false)
const bans = ref([])
const searchQuery = ref('')
const statusFilter = ref('active')
const page = ref(1)
const pageSize = 20
const toast = ref(null)

const showBanModal = ref(false)
const unbanTarget = ref(null)
const editExpireTarget = ref(null)
const expireForm = ref({
  datetime: '',
  permanent: false,
})
const expireFormError = ref('')
const banForm = ref({
  player: '',
  duration: '',
  reason: '',
})

const filteredBans = computed(() => {
  const q = searchQuery.value.toLowerCase()
  return bans.value.filter((b) => {
    if (statusFilter.value === 'active' && !b.active) return false
    if (!q) return true

    return [
      String(b.ticket || ''),
      String(b.target || ''),
      String(b.identifier || ''),
      String(b.reason || ''),
      String(b.banned_by || ''),
    ].some((v) => v.toLowerCase().includes(q))
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredBans.value.length / pageSize)))

const pagedBans = computed(() => {
  const start = (page.value - 1) * pageSize
  return filteredBans.value.slice(start, start + pageSize)
})

function showToast(ok, msg) {
  toast.value = { ok, msg }
  setTimeout(() => {
    toast.value = null
  }, 4000)
}

function formatRemaining(seconds) {
  if (seconds === null || seconds === undefined) return '永久'
  const total = Math.max(0, Number(seconds) || 0)
  const d = Math.floor(total / 86400)
  const h = Math.floor((total % 86400) / 3600)
  const m = Math.floor((total % 3600) / 60)
  if (d > 0) return `${d}天${h}小时`
  if (h > 0) return `${h}小时${m}分钟`
  return `${m}分钟`
}

function loadBans() {
  if (!activeServerKey.value) return
  loading.value = true
  loadError.value = ''

  window.__tshockSend?.({
    type: 'list_bans',
    msg_id: `bans-list-${Date.now()}`,
    timestamp: Date.now(),
    payload: {
      agent_key: activeServerKey.value,
    },
  })
}

function openBanModal() {
  banForm.value = { player: '', duration: '', reason: '' }
  showBanModal.value = true
}

function closeBanModal() {
  showBanModal.value = false
}

function submitBan() {
  if (!banForm.value.player) return
  submitting.value = true

  window.__tshockSend?.({
    type: 'player_action',
    msg_id: `bans-add-${Date.now()}`,
    timestamp: Date.now(),
    payload: {
      agent_key: activeServerKey.value,
      action: 'ban',
      player: banForm.value.player,
      duration: banForm.value.duration,
      reason: banForm.value.reason,
    },
  })
}

function confirmUnban(row) {
  unbanTarget.value = row
}

function openEditExpireModal(row) {
  editExpireTarget.value = row
  expireFormError.value = ''
  if (row.expiration_time) {
    expireForm.value = {
      datetime: String(row.expiration_time).replace(' ', 'T').slice(0, 16),
      permanent: false,
    }
  } else {
    expireForm.value = {
      datetime: '',
      permanent: true,
    }
  }
}

function submitUnban() {
  if (!unbanTarget.value) return
  submitting.value = true

  window.__tshockSend?.({
    type: 'unban_by_ticket',
    msg_id: `bans-unban-${Date.now()}`,
    timestamp: Date.now(),
    payload: {
      agent_key: activeServerKey.value,
      ticket: unbanTarget.value.ticket,
    },
  })
}

function submitUpdateExpire() {
  if (!editExpireTarget.value) return
  expireFormError.value = ''

  if (!expireForm.value.permanent && !expireForm.value.datetime) {
    expireFormError.value = '请选择到期时间，或勾选“设为永久封禁”'
    return
  }

  submitting.value = true

  window.__tshockSend?.({
    type: 'update_ban_expiration',
    msg_id: `bans-update-exp-${Date.now()}`,
    timestamp: Date.now(),
    payload: {
      agent_key: activeServerKey.value,
      ticket: editExpireTarget.value.ticket,
      expiration_time: expireForm.value.datetime,
      permanent: expireForm.value.permanent,
    },
  })
}

function onWsMessage(e) {
  const pkt = e.detail
  const p = pkt.payload || {}

  if (pkt.type === 'list_bans_resp') {
    loading.value = false
    if (p.success) {
      bans.value = Array.isArray(p.bans) ? p.bans : []
      page.value = 1
    } else {
      loadError.value = p.msg || '加载封禁失败'
    }
    return
  }

  if (pkt.type === 'player_action_resp' && p.action === 'ban') {
    submitting.value = false
    showToast(p.success ?? false, p.msg || (p.success ? '封禁成功' : '封禁失败'))
    if (p.success) {
      closeBanModal()
      loadBans()
    }
    return
  }

  if (pkt.type === 'unban_by_ticket_resp') {
    submitting.value = false
    showToast(p.success ?? false, p.msg || (p.success ? '解封成功' : '解封失败'))
    if (p.success) {
      unbanTarget.value = null
      loadBans()
    }
    return
  }

  if (pkt.type === 'update_ban_expiration_resp') {
    submitting.value = false
    showToast(p.success ?? false, p.msg || (p.success ? '修改到期时间成功' : '修改到期时间失败'))
    if (p.success) {
      editExpireTarget.value = null
      expireFormError.value = ''
      expireForm.value = { datetime: '', permanent: false }
      loadBans()
    }
  }
}

onMounted(() => {
  window.addEventListener('ws-message', onWsMessage)
  if (props.agentOnline && activeServerKey.value) loadBans()
})

onUnmounted(() => {
  window.removeEventListener('ws-message', onWsMessage)
})

watch([activeServerKey, () => props.agentOnline], ([key, online]) => {
  if (key && online) loadBans()
  searchQuery.value = ''
  page.value = 1
})

watch([searchQuery, statusFilter], () => {
  page.value = 1
})
</script>

<style scoped>
.bans-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: radial-gradient(circle at 15% 0%, #eff6ff 0, #f8fafc 35%, #f8fafc 100%);
}

.cfg-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
}

.cfg-btn svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.cfg-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.cfg-btn-outline {
  background: #fff;
  color: #374151;
  border: 1px solid #d1d5db;
}

.cfg-btn-outline:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #9ca3af;
}

.cfg-btn-primary {
  background: #3b82f6;
  color: #fff;
}

.cfg-btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.bans-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
  box-sizing: border-box;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.filter-tabs {
  display: flex;
  gap: 4px;
  background: #f1f5f9;
  padding: 4px;
  border-radius: 8px;
}

.tab {
  padding: 6px 14px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  font-size: 13px;
  cursor: pointer;
}

.tab.active {
  background: #fff;
  color: #0f172a;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.search-wrap {
  min-width: min(520px, 100%);
  flex: 1;
}

.search-input {
  width: 100%;
  box-sizing: border-box;
  padding: 9px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  color: #0f172a;
  outline: none;
}

.search-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.12);
}

.state-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  border-radius: 10px;
  font-size: 14px;
  margin-bottom: 16px;
}

.state-empty {
  background: #f8fafc;
  color: #94a3b8;
  border: 1px solid #e2e8f0;
  justify-content: center;
  padding: 60px 24px;
  text-align: center;
}

.state-loading {
  background: #f8fafc;
  color: #64748b;
  justify-content: center;
  padding: 60px 24px;
}

.state-error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.table-wrap {
  overflow-x: auto;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background: #fff;
  }

  .ban-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
    table-layout: auto;
  }

  .ban-table th {
    background: #f8fafc;
    padding: 10px 12px;
    text-align: left;
    font-size: 12px;
    font-weight: 600;
    color: #64748b;
    border-bottom: 1px solid #e2e8f0;
  }

  .ban-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #f1f5f9;
    color: #334155;
    vertical-align: middle;
    word-break: break-all;
    word-wrap: break-word;
    max-width: 200px;
  }
.ban-table tr:last-child td {
  border-bottom: none;
}

.empty-row {
  text-align: center;
  color: #94a3b8;
  padding: 36px;
}

.ticket-tag {
  font-family: monospace;
  font-size: 13px;
  font-weight: 700;
  color: #1d4ed8;
  background: #dbeafe;
  padding: 2px 8px;
  border-radius: 4px;
}

.mono {
  font-family: monospace;
  color: #64748b;
}

.status-pill {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  border-radius: 999px;
  padding: 2px 8px;
}

.status-active {
  color: #166534;
  background: #dcfce7;
}

.status-expired {
  color: #92400e;
  background: #ffedd5;
}

.status-subtext {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: #64748b;
}

.pagination {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  justify-content: center;
}

.page-info {
  font-size: 13px;
  color: #64748b;
}

.toast {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 14px;
  margin-bottom: 16px;
  gap: 12px;
}

.toast-ok {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #bbf7d0;
}

.toast-err {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.toast-close {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: inherit;
  padding: 0;
  margin-left: auto;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-sm {
  padding: 7px 16px;
}

.btn-xs {
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 6px;
}

.btn-primary {
  background: #3b82f6;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-outline {
  background: #fff;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-outline:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #9ca3af;
}

.btn-danger {
  background: #ef4444;
  color: #fff;
}

.btn-danger:hover:not(:disabled) {
  background: #dc2626;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-box {
  background: #fff;
  border-radius: 12px;
  width: 460px;
  max-width: 95vw;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
}

.modal-box-sm {
  width: 400px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px 14px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.modal-close {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #94a3b8;
  padding: 0;
}

.modal-close:hover {
  color: #0f172a;
}

.modal-body {
  padding: 20px 22px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 22px;
  border-top: 1px solid #e2e8f0;
}

.form-field {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 6px;
}

.required {
  color: #ef4444;
}

.form-input {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  color: #0f172a;
  outline: none;
}

.form-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.12);
}

.confirm-sub {
  margin-top: 4px;
  color: #64748b;
  font-size: 13px;
}

.check-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #334155;
  font-size: 13px;
}

.form-error {
  margin-top: 8px;
  color: #dc2626;
  font-size: 12px;
}

@media (max-width: 900px) {
  .bans-body {
    padding-left: 16px;
    padding-right: 16px;
  }

  .toolbar {
    align-items: stretch;
  }

  .search-wrap {
    min-width: 100%;
  }
}
</style>
