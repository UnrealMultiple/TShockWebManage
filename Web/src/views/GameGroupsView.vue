<template>
  <div class="gg-page">
    <PageHeader title="游戏权限组管理" heading-tag="h1">
      <template #actions>
        <button class="btn btn-sm btn-outline" @click="loadGroups" :disabled="loading || !agentOnline || !activeServerKey">
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
      </template>
    </PageHeader>

    <div class="gg-body">
      <!-- Agent 离线 -->
      <AgentOfflineNotice v-if="!agentOnline" message="Agent 未连接，无法管理权限组。请先启动服务器。" />

      <!-- 无服务器 -->
      <div v-else-if="!activeServerKey" class="state-box state-empty">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        </svg>
        <p>请先在左侧选择一个服务器</p>
      </div>

      <!-- 加载中 -->
      <div v-else-if="loading" class="state-box state-loading">
        <div class="spinner"></div>
        <span>正在加载数据…</span>
      </div>

      <!-- 错误 -->
      <div v-else-if="loadError" class="state-box state-error">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <div>
          <strong>加载失败</strong>
          <p>{{ loadError }}</p>
          <button class="btn btn-sm btn-outline" style="margin-top:8px" @click="loadGroups">重试</button>
        </div>
      </div>

      <!-- 核心表格展示 -->
      <template v-else>
        <div v-if="toast" :class="['toast', toast.ok ? 'toast-ok' : 'toast-err']">
          {{ toast.msg }}
          <button class="toast-close" @click="toast = null">✕</button>
        </div>

        <div class="card-panel">
          <!-- 工具栏 -->
          <div class="body-toolbar">
            <div class="toolbar-left">
              <div class="search-wrap">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <input
                  v-model.trim="searchKeyword"
                  class="search-input"
                  placeholder="搜索组名 / 父组 / 前缀"
                />
              </div>
              <span class="result-hint">已显示 {{ filteredGroups.length }} / {{ groups.length }} 项</span>
            </div>
            <button class="btn btn-sm btn-primary" @click="openCreate" :disabled="!agentOnline || !activeServerKey">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0">
                <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
              新建权限组
            </button>
          </div>

          <div class="groups-table-wrap">
            <table class="groups-table">
              <thead>
                <tr>
                  <th>组名 (Name)</th>
                  <th>权限数量</th>
                  <th>继承父组 (Parent)</th>
                  <th>聊天前缀</th>
                  <th>聊天后缀</th>
                  <th>聊天颜色</th>
                  <th style="text-align: right;">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!filteredGroups.length">
                  <td colspan="7" class="empty-row">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="3" x2="9" y2="21"/>
                    </svg>
                    <div>没有匹配的权限组数据</div>
                  </td>
                </tr>
                <tr v-for="g in filteredGroups" :key="g.name" class="table-row">
                  <td>
                    <div style="display:flex;align-items:center;gap:6px;">
                      <span class="group-name">{{ g.name }}</span>
                      <span v-if="g.name === 'superadmin'" class="badge-super">超级管理</span>
                      <span v-else-if="g.name === 'default'" class="badge-default">默认</span>
                    </div>
                  </td>
                  <td>
                    <span class="view-badge">{{ g.permissions?.length ?? 0 }} 项</span>
                  </td>
                  <td>
                    <span v-if="g.parent" class="parent-badge">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px;margin-right:4px;"><polyline points="9 10 4 15 9 20"/><path d="M20 4v7a4 4 0 0 1-4 4H4"/></svg>
                      {{ g.parent }}
                    </span>
                    <span v-else class="muted">—</span>
                  </td>
                  <td><span v-if="g.prefix" class="chat-prefix">{{ g.prefix }}</span><span v-else class="muted">—</span></td>
                  <td><span v-if="g.suffix" class="chat-prefix">{{ g.suffix }}</span><span v-else class="muted">—</span></td>
                  <td>
                    <div v-if="g.chat_color" style="display:flex;align-items:center;gap:6px;">
                      <span class="color-preview" :style="{ backgroundColor: `rgb(${g.chat_color})` }"></span>
                      <span class="chat-prefix">{{ g.chat_color }}</span>
                    </div>
                    <span v-else class="muted">—</span>
                  </td>
                  <td>
                    <div class="row-actions">
                        <button class="btn btn-xs btn-outline" 
                          :disabled="g.name === 'superadmin'" 
                          :title="g.name === 'superadmin' ? '系统内置最高权限组，不可修改' : ''"
                          @click="openEdit(g)">授权/编辑</button>
                      <button class="btn btn-xs btn-danger"
                        :disabled="g.name === 'superadmin' || g.name === 'default'"
                        :title="(g.name === 'superadmin' || g.name === 'default') ? '内置组不可删除' : ''"
                        @click="confirmDelete(g)">删除</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>

    <!-- ── 穿梭框式交互模态框 ── -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-box modal-box-large">
        <div class="modal-header">
          <h3>{{ editingGroup ? '配置权限组：' + editingGroup.name : '新建权限组' }}</h3>
          <button class="modal-close" @click="closeModal">✕</button>
        </div>
        
        <div class="modal-body modal-split-body">
          <!-- 左侧：基础表单 和 已选权限 -->
          <div class="modal-form-col">
            <div class="form-row-2">
              <div class="form-field">
                <label class="form-label">标识组名 <span class="required">*</span></label>
                  <input v-model="form.name" class="form-input" placeholder="小写字母组合，如 vip" :disabled="editingGroup?.name === 'default'" :title="editingGroup?.name === 'default' ? '内置默认组不能更改名称' : ''" />
              </div>
              <div class="form-field">
                <label class="form-label">继承父组</label>
                <input v-model="form.parent" class="form-input" placeholder="如 default（留空则不继承）" />
              </div>
            </div>
            <div class="form-row-2">
              <div class="form-field">
                <label class="form-label">聊天前缀</label>
                <input v-model="form.prefix" class="form-input" placeholder="如 [VIP]" />
              </div>
              <div class="form-field">
                <label class="form-label">聊天后缀</label>
                <input v-model="form.suffix" class="form-input" placeholder="（非必填）" />
              </div>
              <div class="form-field">
                <label class="form-label">聊天颜色 (RGB)</label>
                <div style="display:flex; gap:8px;">
                  <input type="color" v-model="chatColorHex" class="form-color-picker" title="点击选择颜色" />
                  <input v-model="form.chat_color" class="form-input" placeholder="如 255,255,255" />
                </div>
              </div>
            </div>
            
            <div class="form-field flex-fill-field">
              <div class="perm-title-area">
                <label class="form-label">本组权限 ({{ form.permissions.length }})</label>
                <button class="btn btn-xs btn-outline btn-danger-text" v-if="form.permissions.length" @click="form.permissions = []">清空</button>
              </div>
              <div class="perm-input-wrap">
                <input
                  v-model="newPermInput"
                  class="form-input"
                  placeholder="手动输入权限名（回车添加）"
                  @keydown.enter.prevent="addPerm"
                />
                <button class="btn btn-sm btn-primary" @click="addPerm">添加</button>
              </div>
              <div class="perm-tags-box large-tags-box">
                <div v-if="!form.permissions.length" class="perm-empty-hint">尚未配置任何权限，请在右侧库中点击分配</div>
                <span v-for="p in form.permissions" :key="p" class="perm-tag">
                  {{ p }}
                  <button class="perm-tag-del" @click="removePerm(p)">×</button>
                </span>
              </div>
            </div>
          </div>

          <!-- 右侧：权限参考与分配池 -->
          <div class="modal-doc-col">
            <div class="doc-header">
              <span class="doc-header-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
                </svg>
                权限词典池
              </span>
              <span class="doc-hint">点击即可分配/取消</span>
            </div>
            <div class="doc-search-box">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              <input v-model.trim="permSearchKeyword" class="doc-search-input" placeholder="搜索功能关键词或节点..." />
            </div>
            <div class="doc-body">
              <div v-if="filteredPerms.length === 0" class="doc-empty">没找到匹配的权限</div>
              
              <div v-for="p in filteredPerms" :key="p.name" 
                   :class="['doc-perm-item', form.permissions.includes(p.name) ? 'doc-perm-added' : '']" 
                   @click="togglePerm(p.name)">
                <div class="doc-perm-head">
                  <span class="doc-perm-name">{{ p.name }}</span>
                  <span class="doc-perm-copy" v-if="form.permissions.includes(p.name)" title="已分配，点击取消">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                  </span>
                  <span class="doc-perm-copy" v-else title="点击分配给当前组">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                  </span>
                </div>
                <div class="doc-perm-desc">{{ p.desc }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn btn-outline" @click="closeModal">取消操作</button>
          <button class="btn btn-primary" @click="submitForm" :disabled="submitting">
            <svg v-if="submitting" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin 1s linear infinite;"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/></svg>
            {{ submitting ? '保存中…' : (editingGroup ? '保存并应用' : '创建权限组') }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── 删除确认模态框 ── -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
      <div class="modal-box modal-box-sm">
        <div class="modal-header">
          <h3>警告：确认删除权限组？</h3>
          <button class="modal-close" @click="deleteTarget = null">✕</button>
        </div>
        <div class="modal-body">
          <p>您即将删除目标组：<strong style="color:#ef4444;font-size:16px;">{{ deleteTarget.name }}</strong></p>
          <p style="color:#64748b;font-size:13px;margin-top:8px;">此操作将从数据库中直接抹除，所有属于该组的玩家可能会丢失权限并退回默认组。操作不可撤销。</p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="deleteTarget = null">取消</button>
          <button class="btn btn-danger" @click="doDelete" :disabled="submitting">
            {{ submitting ? '删除处理中…' : '我已确认，无情删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, inject, watch, computed } from 'vue'
import { PERMISSIONS_LIST } from '@/config/tshock_permissions.js'
import AgentOfflineNotice from '@/components/AgentOfflineNotice.vue'
import PageHeader from '@/components/PageHeader.vue'

const props = defineProps({
  agentOnline: { type: Boolean, default: false },
})

const activeServerKey = inject('activeServerKey', ref(''))

const loading    = ref(false)
const loadError  = ref('')
const groups     = ref([])
const toast      = ref(null)
const showModal  = ref(false)
const editingGroup = ref(null)
const deleteTarget = ref(null)
const submitting   = ref(false)
const reloading    = ref(false)
const saving       = ref(false)
const searchKeyword = ref('')
const permSearchKeyword = ref('')
const newPermInput  = ref('')
const pendingLoadRefId = ref('')
let loadTimeoutTimer = null
let legacyFallbackTimer = null

const form = ref({ name: '', parent: '', prefix: '', suffix: '', chat_color: '255,255,255', permissions: [] })

const chatColorHex = computed({
  get() {
    if (!form.value.chat_color) return '#ffffff'
    const parts = form.value.chat_color.split(',').map(s => parseInt(s.trim()))
    if (parts.length !== 3 || parts.some(isNaN)) return '#ffffff'
    return '#' + parts.map(x => Math.min(255, Math.max(0, x)).toString(16).padStart(2, '0')).join('')
  },
  set(val) {
    if (!val || val.length !== 7) return
    const r = parseInt(val.substring(1, 3), 16)
    const g = parseInt(val.substring(3, 5), 16)
    const b = parseInt(val.substring(5, 7), 16)
    form.value.chat_color = `${r},${g},${b}`
  }
})

const filteredGroups = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return groups.value
  return groups.value.filter((g) => {
    const name = (g.name || '').toLowerCase()
    const parent = (g.parent || '').toLowerCase()
    const prefix = (g.prefix || '').toLowerCase()
    return name.includes(keyword) || parent.includes(keyword) || prefix.includes(keyword)
  })
})

const filteredPerms = computed(() => {
  const keyword = permSearchKeyword.value.trim().toLowerCase()
  if (!keyword) return PERMISSIONS_LIST
  return PERMISSIONS_LIST.filter(p => p.name.toLowerCase().includes(keyword) || p.desc.toLowerCase().includes(keyword))
})

// ── 加载权限组 ────────────────────────────────────────────────────
function loadGroups() {
  if (!activeServerKey.value) return
  if (loading.value) return
  clearTimeout(loadTimeoutTimer)
  clearTimeout(legacyFallbackTimer)
  const reqId = `gg-list-${Date.now()}`
  pendingLoadRefId.value = reqId
  loading.value   = true
  loadError.value = ''

  window.__tshockSend?.({
    type: 'list_game_groups',
    msg_id: reqId,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })

  legacyFallbackTimer = setTimeout(() => {
    if (!loading.value) return
    window.__tshockSend?.({
      type: 'get_groups',
      msg_id: reqId,
      timestamp: Date.now(),
      payload: { agent_key: activeServerKey.value },
    })
  }, 2500)

  loadTimeoutTimer = setTimeout(() => {
    if (!loading.value) return
    loading.value = false
    loadError.value = '请求超时，请确认 Agent 在线且工作正常。'
  }, 10000)
}

// ── 模态框交互与权限控制 ───────────────────────────────────────────
function openCreate() {
  editingGroup.value = null
  form.value = { name: '', parent: '', prefix: '', suffix: '', chat_color: '255,255,255', permissions: [] }
  newPermInput.value = ''
  permSearchKeyword.value = ''
  showModal.value = true
}

function openEdit(g) {
  editingGroup.value = g
  form.value = {
    name:      g.name,
    parent:    g.parent || '',
    prefix:    g.prefix || '',
    suffix:    g.suffix || '',
    chat_color: g.chat_color || '255,255,255',
    permissions: [...(g.permissions || [])],
  }
  newPermInput.value = ''
  permSearchKeyword.value = ''
  showModal.value = true
}

function addPerm() {
  const p = newPermInput.value.trim()
  if (p && !form.value.permissions.includes(p)) {
    form.value.permissions.unshift(p)
  }
  newPermInput.value = ''
}

function removePerm(p) {
  form.value.permissions = form.value.permissions.filter(x => x !== p)
}

function togglePerm(permName) {
  if (form.value.permissions.includes(permName)) {
    removePerm(permName)
  } else {
    form.value.permissions.unshift(permName)
  }
}

function closeModal() {
  showModal.value = false
  editingGroup.value = null
}

function submitForm() {
  const name = form.value.name.trim()
  if (!name) return
  submitting.value = true
  window.__tshockSend?.({
    type: editingGroup.value ? 'update_game_group' : 'create_game_group',
    msg_id: `gg-save-${Date.now()}`,
    timestamp: Date.now(),
    payload: {
      agent_key: activeServerKey.value,
      old_name: editingGroup.value?.name || name,
      name, parent: form.value.parent.trim(),
      prefix: form.value.prefix, suffix: form.value.suffix,
      chat_color: form.value.chat_color,
      permissions: form.value.permissions,
    },
  })
}

function confirmDelete(g) { deleteTarget.value = g }

function doDelete() {
  if (!deleteTarget.value) return
  submitting.value = true
  window.__tshockSend?.({
    type: 'delete_game_group',
    msg_id: `gg-del-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, name: deleteTarget.value.name },
  })
}

function showToast(ok, msg) {
  toast.value = { ok, msg }
  setTimeout(() => { toast.value = null }, 3500)
}

function doReload() {
  if (!activeServerKey.value) return
  reloading.value = true
  window.__tshockSend?.({
    type: 'reload_tshock',
    msg_id: `gg-reload-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

function doSave() {
  if (!activeServerKey.value) return
  saving.value = true
  window.__tshockSend?.({
    type: 'save_world',
    msg_id: `gg-save-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

// ── WS Event Listener ────────────────────────────────────────────────
function onWsMessage(e) {
  const pkt = e.detail
  const p   = pkt.payload || {}

  const isLoadResp = pkt.type === 'list_game_groups_resp' || pkt.type === 'get_groups_resp'
  if (isLoadResp) {
    const refId = p.ref_id || ''
    if (pendingLoadRefId.value && refId && refId !== pendingLoadRefId.value) return

    clearTimeout(loadTimeoutTimer)
    clearTimeout(legacyFallbackTimer)
    loading.value = false
    if (!p.success) {
      loadError.value = p.msg || '加载失败'
      return
    }

    const rawGroups = Array.isArray(p.groups) ? p.groups : []
    groups.value = rawGroups.map((g) => {
      if (typeof g === 'string') {
        return { name: g, parent: '', prefix: '', suffix: '', chat_color: '255,255,255', permissions: [] }
      }
      return {
        name: g?.name || '',
        parent: g?.parent || '',
        prefix: g?.prefix || '',
        suffix: g?.suffix || '',
        chat_color: g?.chat_color || '255,255,255',
        permissions: Array.isArray(g?.permissions) ? g.permissions : [],
      }
    }).filter((g) => !!g.name)

    if (pkt.type === 'get_groups_resp') {
      showToast(false, '警告：当前处于降级模式，无法查看组权限和继承结构。请升级 Agent 插件！')
    }
    return
  }

  if (pkt.type === 'create_game_group_resp' || pkt.type === 'update_game_group_resp') {
    submitting.value = false
    showToast(p.success ?? false, p.msg || (p.success ? '组设置已保存' : '保存失败'))
    if (p.success) { closeModal(); loadGroups() }
    return
  }

  if (pkt.type === 'delete_game_group_resp') {
    submitting.value = false
    showToast(p.success ?? false, p.msg || (p.success ? '成功销毁权限组' : '删除失败'))
    if (p.success) { deleteTarget.value = null; loadGroups() }
    return
  }

  if (pkt.type === 'reload_tshock_resp') {
    reloading.value = false
    showToast(p.success ?? false, p.msg || (p.success ? 'TShock 配置已热重载' : '重载指令异常'))
    return
  }

  if (pkt.type === 'save_world_resp') {
    saving.value = false
    showToast(p.success ?? false, p.msg || (p.success ? '世界存档保存完毕' : '保存失败'))
    return
  }
}

onMounted(() => {
  window.addEventListener('ws-message', onWsMessage)
  if (props.agentOnline && activeServerKey.value) loadGroups()
})
onUnmounted(() => {
  window.removeEventListener('ws-message', onWsMessage)
  clearTimeout(loadTimeoutTimer)
  clearTimeout(legacyFallbackTimer)
})

watch([activeServerKey, () => props.agentOnline], ([key, online]) => {
  if (key && online) loadGroups()
})
</script>

<style scoped>
.gg-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: #f1f5f9; /* modern light blue-gray background */
}

/* ── 主体 ────────────────────────────────────────────────────── */
.gg-body {
  flex: 1; overflow: hidden; padding: 24px 28px; box-sizing: border-box;
  display: flex; flex-direction: column;
}

/* 新版全铺卡片化 */
.card-panel {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05);
  border: 1px solid #e2e8f0;
  overflow: hidden;
}

.body-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 16px 20px;
  border-bottom: 1px solid #f1f5f9;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.search-wrap {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; min-width: 320px;
  border-radius: 8px; box-shadow: inset 0 1px 2px rgb(0 0 0 / 0.02);
  border: 1px solid #cbd5e1; background: #f8fafc; transition: all .2s;
}
.search-wrap:focus-within { background: #fff; border-color: #60a5fa; box-shadow: 0 0 0 2px rgba(59,130,246,.15); }
.search-wrap svg { width: 15px; height: 15px; color: #64748b; }
.search-input { width: 100%; border: none; outline: none; background: transparent; color: #0f172a; font-size: 13px; }
.result-hint { font-size: 12px; color: #94a3b8; font-weight: 500; }

@keyframes spin { to { transform: rotate(360deg); } }

/* ── 列表空状态/错误状态 ──────────────────────────────────────── */
.state-box {
  display: flex; align-items: center; gap: 12px;
  padding: 20px 24px; border-radius: 10px; font-size: 14px; margin-bottom: 16px;
  box-shadow: 0 1px 2px rgb(0 0 0 / 0.05);
}
.state-box svg { width: 22px; height: 22px; flex-shrink: 0; }
.state-empty { background: #fff; color: #94a3b8; border: 1px solid #e2e8f0; justify-content: center; flex-direction: column; padding: 80px 24px; text-align: center; }
.state-empty svg { width: 48px; height: 48px; stroke: #cbd5e1; margin-bottom: 12px; }
.state-loading { background: #fff; color: #64748b; border: 1px solid #e2e8f0; justify-content: center; padding: 80px 24px; flex-direction: row; gap: 12px; }
.state-error { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.state-error svg { stroke: #ef4444; }
.spinner { width: 26px; height: 26px; border: 3px solid #f1f5f9; border-top-color: #3b82f6; border-radius: 50%; animation: spin .7s linear infinite; flex-shrink: 0; }

/* ── 表格本体 ─────────────────────────────────────────────────── */
.groups-table-wrap {
  flex: 1; overflow: auto;
}
.groups-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.groups-table th {
  position: sticky; top: 0; z-index: 2;
  background: #f8fafc; padding: 12px 20px; text-align: left;
  font-size: 13px; font-weight: 600; color: #475569;
  border-bottom: 1px solid #e2e8f0; white-space: nowrap;
}
.groups-table td { padding: 14px 20px; border-bottom: 1px solid #f1f5f9; color: #334155; vertical-align: middle; }
.table-row:hover { background-color: #f8fafc; }
.group-name { font-weight: 600; color: #0f172a; font-size: 15px; }
.badge-super { font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 20px; background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
.badge-default { font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 20px; background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0; }

.view-badge { font-size: 12px; font-weight: 700; color: #3b82f6; background: #eff6ff; padding: 4px 10px; border-radius: 6px; display: inline-block; border: 1px solid #bfdbfe; }
.parent-badge { display: inline-flex; align-items: center; padding: 4px 8px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 13px; color: #475569; font-weight: 500; }
.chat-prefix { font-family: monospace; font-size: 13px; color: #0f172a; background: #f1f5f9; padding: 3px 8px; border-radius: 6px; border: 1px solid #e2e8f0; }
.muted { color: #94a3b8; }
.empty-row { text-align: center; color: #94a3b8; padding: 80px 0 !important; font-size: 14px; }
.row-actions { display: flex; gap: 8px; justify-content: flex-end; }

/* ── Toast ───────────────────────────────────────────────────── */
.toast {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 20px; border-radius: 8px; font-size: 14px; font-weight: 500;
  margin-bottom: 16px; gap: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); z-index: 999;
}
.toast-ok  { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.toast-err { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.toast-close { background: none; border: none; cursor: pointer; font-size: 14px; color: inherit; padding: 0; margin-left: auto; opacity: 0.6; transition: opacity .2s; }
.toast-close:hover { opacity: 1; }

/* ── 按钮系列 ─────────────────────────────────────────────────── */
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; border: none; transition: all 0.2s; white-space: nowrap; }
.btn svg { width: 14px; height: 14px; flex-shrink: 0; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-sm  { padding: 7px 14px; font-size: 13px; }
.btn-xs  { padding: 5px 12px; font-size: 12px; border-radius: 6px; }
.btn-primary { background: #3b82f6; color: #fff; box-shadow: 0 1px 2px rgba(59,130,246,0.3); }
.btn-primary:hover:not(:disabled) { background: #2563eb; transform: translateY(-1px); box-shadow: 0 4px 6px rgba(59,130,246,0.25); }
.btn-primary:active:not(:disabled) { transform: translateY(0); }
.btn-outline { background: #fff; color: #334155; border: 1px solid #cbd5e1; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.btn-outline:hover:not(:disabled) { background: #f8fafc; border-color: #94a3b8; }
.btn-danger { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.btn-danger:hover:not(:disabled) { background: #fee2e2; border-color: #fca5a5; }
.btn-danger-text { color: #dc2626; border-color: transparent; box-shadow: none; padding: 4px 8px; }
.btn-danger-text:hover { background: #fef2f2; border-color: #fecaca; }

/* ── 穿梭框大模态框设计 ────────────────────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(15, 23, 42, 0.5); backdrop-filter: blur(2px);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}
@keyframes fadeIn { from{ opacity:0 } to{opacity:1} }
.modal-box {
  background: #fff; border-radius: 12px; width: 500px; max-width: 95vw;
  box-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.25); display: flex; flex-direction: column;
  max-height: 90vh; animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes slideUp { from{ transform:translateY(15px); opacity:0 } to{transform:none;opacity:1} }

.modal-box-large { width: 880px; }
.modal-box-sm { width: 420px; }

.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 24px; border-bottom: 1px solid #e2e8f0; background: #fff;
  border-radius: 12px 12px 0 0;
}
.modal-header h3 { margin: 0; font-size: 16px; font-weight: 700; color: #0f172a; }
.modal-close { background: #f1f5f9; border: none; font-size: 16px; cursor: pointer; color: #64748b; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; transition: all .2s; }
.modal-close:hover { background: #e2e8f0; color: #0f172a; }

.modal-split-body {
  display: flex; gap: 0; padding: 0 !important; overflow: hidden; height: 500px;
}
.modal-form-col {
  flex: 1; min-width: 0; padding: 24px; overflow-y: auto; display: flex; flex-direction: column;
}
.modal-doc-col {
  width: 320px; flex-shrink: 0; border-left: 1px solid #e2e8f0;
  background: #f8fafc; display: flex; flex-direction: column; overflow: hidden;
}

.modal-body { padding: 24px; overflow-y: auto; font-size: 14px; color: #334155; line-height: 1.5; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 24px; background: #f8fafc; border-top: 1px solid #e2e8f0; border-radius: 0 0 12px 12px; }

/* 表单细节 */
.form-row-2 { display: flex; gap: 16px; }
.form-row-2 .form-field { flex: 1; }
.color-preview { display: inline-block; width: 14px; height: 14px; border-radius: 50%; border: 1px solid #cbd5e1; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); }
.form-color-picker { 
  width: 38px; height: 38px; padding: 0; border: 1px solid #cbd5e1; 
  border-radius: 8px; cursor: pointer; flex-shrink: 0; background: #fff;
  transition: all .2s; outline: none;
}
.form-color-picker:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.15); }
.form-color-picker::-webkit-color-swatch-wrapper { padding: 4px; }
.form-color-picker::-webkit-color-swatch { border: none; border-radius: 4px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); }
.form-field { margin-bottom: 20px; }
.flex-fill-field { flex: 1; display: flex; flex-direction: column; min-height: 0; margin-bottom: 0; }
.form-label { display: block; font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 8px; }
.required { color: #ef4444; }
.form-input {
  width: 100%; box-sizing: border-box; padding: 9px 12px;
  border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px; color: #0f172a;
  outline: none; transition: all .2s; background: #fff; box-shadow: inset 0 1px 2px rgb(0 0 0 / 0.02);
}
.form-input:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.15); }

/* 左侧权限Tag盒 */
.perm-title-area { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.perm-title-area .form-label { margin-bottom: 0; }
.perm-input-wrap { display: flex; gap: 8px; margin-bottom: 12px; }
.large-tags-box {
  flex: 1; display: flex; align-content: flex-start; flex-wrap: wrap; gap: 8px;
  padding: 16px; background: #fff; border: 1px solid #cbd5e1; border-radius: 8px;
  overflow-y: auto; box-shadow: inset 0 2px 4px rgb(0 0 0 / 0.02);
}
.perm-empty-hint { color: #94a3b8; font-size: 13px; margin: auto; text-align: center; }
.perm-tag {
  display: inline-flex; align-items: center; gap: 6px;
  background: #eff6ff; border: 1px solid #bfdbfe;
  padding: 4px 10px; border-radius: 6px; font-size: 13px; color: #2563eb; font-weight: 500;
  animation: scaleIn .2s forwards;
}
@keyframes scaleIn { from{ transform: scale(0.9); opacity:0; } to{transform:scale(1);opacity:1;} }
.perm-tag:hover { background: #dbeafe; }
.perm-tag-del { background: rgba(255,255,255,0.5); border: none; padding: 2px; height: 18px; width: 18px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #3b82f6; transition: all .15s; }
.perm-tag-del:hover { background: #ef4444; color: #fff; }

/* 右侧权限库字典池 */
.doc-header { padding: 14px 16px 10px; font-weight: 600; color: #1e293b; display: flex; flex-direction: column; gap: 4px; }
.doc-header-title { display: flex; align-items: center; gap: 8px; font-size: 14px; }
.doc-header-title svg { width: 16px; height: 16px; color: #3b82f6; }
.doc-hint { font-size: 11px; color: #64748b; font-weight: normal; margin-left: 24px; }
.doc-search-box { display: flex; align-items: center; gap: 8px; padding: 0 16px 12px; border-bottom: 1px solid #e2e8f0; }
.doc-search-box svg { width: 14px; height: 14px; color: #64748b; flex-shrink: 0; }
.doc-search-input { border: none; outline: none; width: 100%; font-size: 13px; color: #0f172a; background: transparent; }
.doc-search-input::placeholder { color: #94a3b8; }
.doc-body { flex: 1; overflow-y: auto; padding: 12px; }
.doc-empty { text-align: center; color: #94a3b8; font-size: 13px; padding: 24px 0; }

.doc-perm-item {
  padding: 10px 12px; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
  margin-bottom: 8px; cursor: pointer; transition: all 0.2s;
  box-shadow: 0 1px 2px rgb(0 0 0 / 0.02);
}
.doc-perm-item:hover { transform: translateY(-1px); border-color: #cbd5e1; box-shadow: 0 3px 6px rgb(0 0 0 / 0.04); }
.doc-perm-added { border-color: #60a5fa; background: #eff6ff; }
.doc-perm-added:hover { border-color: #3b82f6; background: #dbeafe; }
.doc-perm-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.doc-perm-name { font-size: 12.5px; font-family: monospace; font-weight: 700; color: #1e293b; word-break: break-all; }
.doc-perm-added .doc-perm-name { color: #2563eb; }
.doc-perm-copy { color: #94a3b8; display: flex; }
.doc-perm-copy svg { width: 16px; height: 16px; }
.doc-perm-item:hover .doc-perm-copy { color: #3b82f6; }
.doc-perm-desc { font-size: 12px; color: #475569; line-height: 1.4; }

@media (max-width: 768px) {
  .modal-box-large { width: 95vw; }
  .modal-split-body { flex-direction: column; height: auto; max-height: calc(90vh - 120px); overflow-y: auto; }
  .modal-form-col { flex: none; overflow: visible; padding-bottom: 0; }
  .form-row-2 { flex-direction: column; gap: 0; }
  .large-tags-box { height: 150px; overflow-y: auto; }
  .modal-doc-col { width: 100%; flex: none; border-left: none; border-top: 1px solid #e2e8f0; height: 400px; }
  
  .gg-body { padding: 14px; }
  .body-toolbar { flex-direction: column; align-items: stretch; }
  .toolbar-left { flex-direction: column; align-items: stretch; }
  .search-wrap { min-width: 0; }
  .row-actions { flex-wrap: wrap; }
}
</style>
