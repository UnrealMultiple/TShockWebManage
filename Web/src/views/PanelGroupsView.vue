<template>
  <div class="pg-page">
    <!-- 页头 -->
    <div class="page-header">
      <h1 class="page-title">面板权限组管理</h1>
      <div class="page-header-right">
        <button class="btn btn-sm btn-outline" @click="loadGroups" :disabled="loading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/></svg>
          {{ loading ? '加载中…' : '刷新' }}
        </button>
        <button v-if="isOwner" class="btn btn-sm btn-primary" @click="openCreate">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:13px;height:13px;flex-shrink:0"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          新建权限组
        </button>
      </div>
    </div>

    <div class="pg-body">

    <!-- 无服务器提示 -->
    <div v-if="!activeServer" class="empty-hint-box">
      <div class="empty-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.01a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
      </div>
      <p>请先在左侧选择一个服务器</p>
    </div>

    <template v-else>
      <!-- 权限说明 -->
      <div class="info-banner">
        <span class="info-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
        </span>
        面板权限组决定成员在此服务器面板内能访问哪些功能。内置组不可删除，Owner 可自由新增或编辑自定义组。
      </div>

      <div class="card-panel">
        <div class="body-toolbar">
          <div class="toolbar-left">
            <div class="search-wrap">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              <input
                v-model.trim="searchKeyword"
                class="search-input"
                placeholder="搜索组名 / 描述 / 权限"
              />
            </div>
            <span class="result-hint">已显示 {{ filteredGroups.length }} / {{ groups.length }} 项</span>
          </div>
          <button v-if="isOwner" class="btn btn-sm btn-primary" @click="openCreate">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            新建权限组
          </button>
        </div>

        <div v-if="loading" class="state-box state-loading state-inline">
          <div class="spinner"></div>
          <span>正在加载数据…</span>
        </div>

        <div v-else class="groups-table-wrap">
          <table class="groups-table">
            <thead>
              <tr>
                <th>组名</th>
                <th>权限数量</th>
                <th>成员数量</th>
                <th>继承父组</th>
                <th>描述</th>
                <th>权限预览</th>
                <th style="text-align:right;">操作</th>
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

              <tr v-for="g in filteredGroups" :key="g.id" class="table-row">
                <td>
                  <div class="group-cell">
                    <span class="group-name">{{ g.name }}</span>
                    <span v-if="g.is_builtin" class="badge badge-builtin">内置</span>
                  </div>
                </td>
                <td>
                  <span class="view-badge">{{ (g.effective_permissions || g.permissions || []).length }} 项</span>
                </td>
                <td><span class="member-text">{{ g.member_count || 0 }} 名</span></td>
                <td>
                  <span v-if="g.parent_group_name" class="parent-badge">{{ g.parent_group_name }}</span>
                  <span v-else class="muted">无</span>
                </td>
                <td>
                  <span class="desc-text">{{ g.description || '暂无描述' }}</span>
                </td>
                <td>
                  <div class="perm-preview-wrap">
                    <span
                      v-for="perm in (g.effective_permissions || g.permissions || []).slice(0, 3)"
                      :key="perm"
                      :class="['perm-preview', permTagClass(perm)]"
                    >{{ perm }}</span>
                    <span v-if="(g.effective_permissions || g.permissions || []).length > 3" class="perm-more">+{{ (g.effective_permissions || g.permissions || []).length - 3 }}</span>
                    <span v-if="!(g.effective_permissions || g.permissions || []).length" class="muted">无权限</span>
                  </div>
                </td>
                <td>
                  <div class="row-actions" v-if="isOwner">
                    <button class="btn btn-xs btn-outline" @click="openEdit(g)">编辑</button>
                    <button
                      class="btn btn-xs btn-danger"
                      :disabled="g.is_builtin"
                      :title="g.is_builtin ? '内置组不可删除' : ''"
                      @click="confirmDelete(g)"
                    >删除</button>
                  </div>
                  <span v-else class="muted">仅 Owner 可操作</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    </div><!-- /pg-body -->

    <!-- ── 新建/编辑 模态框 ─────────────────────────────────────── -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-box">
        <div class="modal-header">
          <h3>{{ editingGroup ? '编辑权限组' : '新建权限组' }}</h3>
          <button class="modal-close" @click="closeModal">✕</button>
        </div>
        <div class="modal-body">
          <!-- 名称（内置组只读） -->
          <div class="form-field">
            <label class="form-label">组名 <span class="required">*</span></label>
            <input
              v-model="form.name"
              class="form-input"
              :disabled="editingGroup?.is_builtin"
              placeholder="如 moderator"
            />
          </div>
          <!-- 描述 -->
          <div class="form-field">
            <label class="form-label">描述</label>
            <input v-model="form.description" class="form-input" placeholder="权限组用途说明（可选）" />
          </div>
          <div class="form-field">
            <label class="form-label">继承父组</label>
            <select v-model="form.parent_group_id" class="form-input">
              <option :value="null">不继承</option>
              <option v-for="g in parentCandidateGroups" :key="g.id" :value="g.id">{{ g.name }}</option>
            </select>
          </div>
          <!-- 权限选择 -->
          <div class="form-field">
            <label class="form-label">权限</label>
            <div class="perm-section">
              <div v-for="sec in FORM_PERMISSION_SECTIONS" :key="sec.key">
                <div class="perm-group-title">{{ sec.title }}</div>
                <div class="perm-checks">
                  <label v-for="p in sec.items" :key="p.value" class="perm-check">
                    <input
                      type="checkbox"
                      :value="p.value"
                      v-model="form.permissions"
                      :disabled="sec.key === 'tshock' ? (hasWildcard || hasTshockWild) : hasWildcard"
                    />
                    <span class="perm-check-label">{{ p.label }}</span>
                    <span :class="['perm-tag-sm', sec.key === 'panel' ? 'tag-panel' : 'tag-tshock']">{{ p.value }}</span>
                  </label>
                </div>
              </div>

              <div class="perm-group-title">超级权限</div>
              <div class="perm-checks">
                <label class="perm-check perm-check-wild">
                  <input type="checkbox" value="tshock.*" v-model="form.permissions" :disabled="hasWildcard" />
                  <span class="perm-check-label">全部 TShock 管理权限</span>
                  <span class="perm-tag-sm tag-tshock">tshock.*</span>
                </label>
                <label class="perm-check perm-check-wild">
                  <input type="checkbox" value="*" v-model="form.permissions" />
                  <span class="perm-check-label">全部权限（* 通配）</span>
                  <span class="perm-tag-sm tag-super">*</span>
                </label>
              </div>
            </div>
          </div>
          <!-- 自定义权限输入 -->
          <div class="form-field">
            <label class="form-label">追加自定义权限</label>
            <div class="custom-perm-row">
              <input
                v-model="customPerm"
                class="form-input"
                placeholder="输入权限字符串后回车添加"
                @keydown.enter.prevent="addCustomPerm"
              />
              <button class="btn btn-sm btn-outline" @click="addCustomPerm">添加</button>
            </div>
            <div v-if="customPerms.length" class="custom-perm-tags">
              <span v-for="cp in customPerms" :key="cp" class="perm-tag tag-custom">
                {{ cp }}
                <button class="tag-remove" @click="removeCustomPerm(cp)">×</button>
              </span>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="closeModal">取消</button>
          <button class="btn btn-primary" @click="submitForm" :disabled="saving">
            {{ saving ? '保存中…' : '保存' }}
          </button>
        </div>
        <p v-if="formError" class="form-error">{{ formError }}</p>
      </div>
    </div>

    <!-- ── 删除确认 ──────────────────────────────────────────────── -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
      <div class="modal-box modal-sm">
        <div class="modal-header">
          <h3>确认删除</h3>
          <button class="modal-close" @click="deleteTarget = null">✕</button>
        </div>
        <div class="modal-body">
          <p>确认删除权限组 <strong>「{{ deleteTarget.name }}」</strong>？该组内的成员将失去分配。</p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="deleteTarget = null">取消</button>
          <button class="btn btn-danger" @click="doDelete" :disabled="deleting">
            {{ deleting ? '删除中…' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, watch } from 'vue'
import {
  listPanelGroups,
  createPanelGroup,
  updatePanelGroup,
  deletePanelGroup,
} from '@/api/servers'

// ── 注入全局状态 ──────────────────────────────────────────────────
const activeServer = inject('activeServer', ref(null))
const canManage    = inject('canManageActiveServer', ref(false))

const isOwner = computed(() => {
  const s = activeServer.value
  if (!s) return false
  return s.server_role === 'owner' || s.panel_group_name === '服主'
})

// ── 预设权限列表 ──────────────────────────────────────────────────
const PANEL_PERMISSION_PLAN = [
  {
    key: 'panel-core',
    title: '面板核心访问',
    items: [
      { value: 'panel.dashboard', label: '仪表盘', desc: '查看服务器状态与在线信息。' },
      { value: 'panel.users', label: '用户管理', desc: '管理成员与角色绑定。' },
      { value: 'panel.console', label: '控制台', desc: '执行控制台命令。' },
      { value: 'panel.files', label: '文件管理', desc: '读取并修改服务器文件。' },
      { value: 'panel.features', label: '面板功能管理', desc: '开关功能模块。' },
      { value: 'panel.groups', label: '面板权限组管理', desc: '管理面板权限组定义。' },
      { value: 'panel.characters', label: '我的角色', desc: '允许访问角色相关页面。' },
      { value: 'panel.inventory.view.self', label: '查看自己背包', desc: '允许查看自己角色背包（只读）。' },
      { value: 'panel.inventory.view.others', label: '查看他人背包', desc: '允许查看其他角色背包（只读）。' },
    ],
  },
  {
    key: 'tshock-ops',
    title: 'TShock 运营管理',
    items: [
      { value: 'tshock.startup', label: '启动脚本', desc: '编辑启动脚本参数。' },
      { value: 'tshock.motd', label: '欢迎消息', desc: '编辑 MOTD 欢迎信息。' },
      { value: 'tshock.config', label: 'TShock 配置', desc: '编辑 tshock/config。' },
      { value: 'tshock.ssc', label: 'SSC 设置', desc: '管理 SSC 同步和角色控制。' },
      { value: 'tshock.plugins', label: '插件管理', desc: '管理插件安装、配置和更新。' },
      { value: 'tshock.groups', label: '游戏权限组', desc: '管理游戏内权限组。' },
      { value: 'tshock.bans', label: '封禁管理', desc: '管理用户封禁记录。' },
      { value: 'tshock.banlists', label: '图格物品弹幕封禁', desc: '管理 banlists 相关条目。' },
    ],
  },
  {
    key: 'wildcard',
    title: '通配权限',
    items: [
      { value: 'tshock.*', label: '全部 TShock 权限', desc: '授予全部 tshock.* 权限。' },
      { value: '*', label: '全部权限', desc: '授予全部权限，慎用。' },
    ],
  },
]

const FORM_PERMISSION_SECTIONS = [
  { key: 'panel', title: '面板功能', items: PANEL_PERMISSION_PLAN[0].items },
  { key: 'tshock', title: 'TShock 管理', items: PANEL_PERMISSION_PLAN[1].items },
]

const PANEL_PERMS = PANEL_PERMISSION_PLAN[0].items
const TSHOCK_PERMS = PANEL_PERMISSION_PLAN[1].items

// ── 数据 ──────────────────────────────────────────────────────────
const groups  = ref([])
const loading = ref(false)
const searchKeyword = ref('')

const filteredGroups = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return groups.value
  return groups.value.filter((g) => {
    const name = (g.name || '').toLowerCase()
    const desc = (g.description || '').toLowerCase()
    const parent = (g.parent_group_name || '').toLowerCase()
    const directPerms = Array.isArray(g.permissions) ? g.permissions.join(' ').toLowerCase() : ''
    const effectivePerms = Array.isArray(g.effective_permissions) ? g.effective_permissions.join(' ').toLowerCase() : ''
    return name.includes(keyword) || desc.includes(keyword) || parent.includes(keyword) || directPerms.includes(keyword) || effectivePerms.includes(keyword)
  })
})

const parentCandidateGroups = computed(() => {
  const editingId = editingGroup.value?.id
  return groups.value.filter((g) => g.id !== editingId)
})

async function loadGroups() {
  const sid = activeServer.value?.id
  if (!sid) return
  loading.value = true
  try {
    const res = await listPanelGroups(sid)
    groups.value = res.data || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

watch(() => activeServer.value?.id, (id) => { if (id) loadGroups() })
onMounted(() => { if (activeServer.value?.id) loadGroups() })

// ── 权限标签样式 ──────────────────────────────────────────────────
function permTagClass(perm) {
  if (perm === '*') return 'tag-super'
  if (perm.startsWith('tshock.')) return 'tag-tshock'
  if (perm.startsWith('panel.')) return 'tag-panel'
  return 'tag-custom'
}

// ── 新建/编辑 模态框 ──────────────────────────────────────────────
const showModal    = ref(false)
const editingGroup = ref(null)
const saving       = ref(false)
const formError    = ref('')
const customPerm   = ref('')

const form = ref({ name: '', description: '', parent_group_id: null, permissions: [] })

const KNOWN_PERMS = [...PANEL_PERMS.map(p => p.value), ...TSHOCK_PERMS.map(p => p.value), 'tshock.*', '*']

const customPerms = computed(() => form.value.permissions.filter(p => !KNOWN_PERMS.includes(p)))
const hasWildcard  = computed(() => form.value.permissions.includes('*'))
const hasTshockWild = computed(() => form.value.permissions.includes('tshock.*'))

function addCustomPerm() {
  const v = customPerm.value.trim()
  if (v && !form.value.permissions.includes(v)) {
    form.value.permissions.push(v)
  }
  customPerm.value = ''
}

function removeCustomPerm(p) {
  form.value.permissions = form.value.permissions.filter(x => x !== p)
}

function openCreate() {
  editingGroup.value = null
  form.value = { name: '', description: '', parent_group_id: null, permissions: [] }
  customPerm.value = ''
  formError.value = ''
  showModal.value = true
}

function openEdit(g) {
  editingGroup.value = g
  form.value = {
    name: g.name,
    description: g.description || '',
    parent_group_id: g.parent_group_id ?? null,
    permissions: [...g.permissions],
  }
  customPerm.value = ''
  formError.value = ''
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  editingGroup.value = null
}

async function submitForm() {
  formError.value = ''
  const name = form.value.name.trim()
  if (!editingGroup.value && !name) {
    formError.value = '组名不能为空'
    return
  }
  const sid = activeServer.value?.id
  saving.value = true
  try {
    if (editingGroup.value) {
      const payload = {
        description: form.value.description,
        parent_group_id: form.value.parent_group_id,
        permissions: form.value.permissions,
      }
      if (!editingGroup.value.is_builtin) payload.name = name
      await updatePanelGroup(sid, editingGroup.value.id, payload)
    } else {
      await createPanelGroup(sid, {
        name,
        description: form.value.description,
        parent_group_id: form.value.parent_group_id,
        permissions: form.value.permissions,
      })
    }
    closeModal()
    await loadGroups()
  } catch (e) {
    formError.value = e.message || '操作失败'
  } finally {
    saving.value = false
  }
}

// ── 删除确认 ──────────────────────────────────────────────────────
const deleteTarget = ref(null)
const deleting     = ref(false)

function confirmDelete(g) {
  deleteTarget.value = g
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await deletePanelGroup(activeServer.value.id, deleteTarget.value.id)
    deleteTarget.value = null
    await loadGroups()
  } catch (e) {
    alert(e.message || '删除失败')
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped>
.pg-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: #f1f5f9;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 28px 16px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.05);
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 12px;
  z-index: 10;
}

.page-title {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.01em;
}

.page-header-right {
  display: flex;
  gap: 8px;
}

.pg-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
  box-sizing: border-box;
}

.card-panel {
  display: flex;
  flex-direction: column;
  min-height: 520px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05);
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
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  min-width: 320px;
  border-radius: 8px;
  box-shadow: inset 0 1px 2px rgb(0 0 0 / 0.02);
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  transition: all .2s;
}

.search-wrap:focus-within {
  background: #fff;
  border-color: #60a5fa;
  box-shadow: 0 0 0 2px rgba(59,130,246,.15);
}

.search-wrap svg { width: 15px; height: 15px; color: #64748b; }

.search-input {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  color: #0f172a;
  font-size: 13px;
}

.result-hint { font-size: 12px; color: #94a3b8; font-weight: 500; }

.groups-table-wrap {
  flex: 1;
  overflow: auto;
}

.groups-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.groups-table th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #f8fafc;
  padding: 12px 20px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
  white-space: nowrap;
}

.groups-table td {
  padding: 14px 20px;
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
  vertical-align: middle;
}

.table-row:hover {
  background-color: #f8fafc;
}

.group-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.group-name { font-weight: 600; color: #0f172a; font-size: 15px; }

.view-badge {
  font-size: 12px;
  font-weight: 700;
  color: #3b82f6;
  background: #eff6ff;
  padding: 4px 10px;
  border-radius: 6px;
  display: inline-block;
  border: 1px solid #bfdbfe;
}

.member-text { font-size: 13px; color: #475569; }
.desc-text { color: #475569; }

.parent-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 13px;
  color: #475569;
  font-weight: 500;
}

.perm-preview-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.perm-preview {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 6px;
  font-weight: 500;
}

.perm-more {
  font-size: 12px;
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  padding: 2px 7px;
  border-radius: 999px;
}

.muted { color: #94a3b8; }

.row-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.empty-row {
  text-align: center;
  color: #94a3b8;
  padding: 80px 0 !important;
  font-size: 14px;
}

.empty-row svg {
  width: 28px;
  height: 28px;
  margin-bottom: 6px;
}

.state-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  border-radius: 10px;
  font-size: 14px;
}

.state-loading {
  background: #fff;
  color: #64748b;
  border: 1px solid #e2e8f0;
  justify-content: center;
  padding: 80px 24px;
}

.state-inline {
  margin: 16px;
}

.spinner {
  width: 26px;
  height: 26px;
  border: 3px solid #f1f5f9;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin .7s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-hint-box {
  text-align: center;
  padding: 80px 24px;
  color: #94a3b8;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}

.empty-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 12px;
  color: #cbd5e1;
}

.empty-icon svg {
  width: 100%;
  height: 100%;
}

.info-banner {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  padding: 12px 14px;
  font-size: 13px;
  color: #1e40af;
  margin-bottom: 14px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.info-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  margin-top: 1px;
}

.info-icon svg {
  width: 100%;
  height: 100%;
}

.pc-title { font-size: 14px; font-weight: 700; color: #0f172a; }
.pc-sub { font-size: 12px; color: #64748b; margin-top: 4px; margin-bottom: 10px; }
.pc-section { border-top: 1px solid #f1f5f9; padding-top: 10px; margin-top: 10px; }
.pc-section:first-of-type { border-top: none; margin-top: 0; padding-top: 0; }
.pc-section-title { font-size: 12px; font-weight: 700; color: #334155; margin-bottom: 8px; }
.pc-items { display: flex; flex-direction: column; gap: 8px; }
.pc-item { padding: 8px; border: 1px solid #e2e8f0; border-radius: 8px; background: #f8fafc; }
.pc-item-main { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.pc-item-label { font-size: 12px; font-weight: 600; color: #1e293b; }
.pc-item-desc { font-size: 11px; color: #64748b; margin-top: 4px; line-height: 1.45; }

.badge { display: inline-block; padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-builtin { background: #e0e7ff; color: #4338ca; border: 1px solid #c7d2fe; }

.perm-tag {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.tag-super { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
.tag-tshock { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.tag-panel { background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }
.tag-custom { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  cursor: pointer;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 16px;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn svg { width: 12px; height: 12px; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-primary {
  background: #3b82f6;
  color: #fff;
  box-shadow: 0 1px 2px rgba(59, 130, 246, 0.3);
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(59, 130, 246, 0.25);
}

.btn-outline {
  background: #fff;
  border: 1px solid #cbd5e1;
  color: #334155;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.btn-outline:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #94a3b8;
}

.btn-danger {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.btn-danger:hover:not(:disabled) {
  background: #fee2e2;
  border-color: #fca5a5;
}

.btn-sm { padding: 7px 14px; font-size: 13px; }
.btn-xs { padding: 5px 12px; font-size: 12px; border-radius: 6px; }

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-box {
  background: #fff;
  border-radius: 12px;
  width: 560px;
  max-width: 95vw;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.25);
  animation: slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slideUp {
  from { transform: translateY(12px); opacity: 0; }
  to { transform: none; opacity: 1; }
}

.modal-sm { width: 400px; }

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h3 { font-size: 16px; font-weight: 700; color: #1e293b; margin: 0; }

.modal-close {
  background: #f1f5f9;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: #64748b;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.modal-close:hover { background: #e2e8f0; color: #0f172a; }

.modal-body { padding: 20px; }

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 20px;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
}

.form-field { margin-bottom: 16px; }
.form-label { display: block; font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 6px; }
.required { color: #ef4444; }

.form-input {
  width: 100%;
  box-sizing: border-box;
  padding: 9px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 13px;
  color: #0f172a;
  outline: none;
  transition: all 0.2s;
  background: #fff;
  box-shadow: inset 0 1px 2px rgb(0 0 0 / 0.02);
}

.form-input:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.15); }
.form-input:disabled { background: #f8fafc; color: #94a3b8; }
.form-error { color: #ef4444; font-size: 13px; text-align: center; padding: 0 20px 12px; }

.perm-section {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 14px;
  max-height: 260px;
  overflow-y: auto;
  background: #fff;
}

.perm-group-title {
  font-size: 11px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: .05em;
  margin: 10px 0 6px;
}

.perm-group-title:first-child { margin-top: 0; }
.perm-checks { display: flex; flex-direction: column; gap: 4px; }

.perm-check {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
  transition: background 0.15s;
}

.perm-check:hover { background: #f8fafc; }
.perm-check input { cursor: pointer; flex-shrink: 0; }
.perm-check-label { flex: 1; }
.perm-check-wild { border-top: 1px dashed #e2e8f0; margin-top: 4px; padding-top: 8px; }

.perm-tag-sm { padding: 1px 6px; border-radius: 4px; font-size: 11px; font-weight: 500; }

.custom-perm-row { display: flex; gap: 8px; }
.custom-perm-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }

.tag-remove {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 13px;
  color: inherit;
  padding: 0 0 0 4px;
  line-height: 1;
}

@media (max-width: 1200px) {
  .body-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-left {
    flex-direction: column;
    align-items: stretch;
  }

  .search-wrap {
    min-width: 0;
  }
}

@media (max-width: 768px) {
  .page-header {
    padding: 18px 14px 14px;
  }

  .pg-body {
    padding: 14px;
  }

  .row-actions {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}
</style>
