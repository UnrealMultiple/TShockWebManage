<template>
  <div class="pg-page">
    <!-- 页头 -->
    <div class="page-header">
      <h1 class="page-title">面板权限组管理</h1>
      <div class="header-actions">
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

      <div class="pg-layout">
        <section class="pg-main">
          <!-- 加载中 -->
          <div v-if="loading" class="loading-state">加载中...</div>

          <!-- 权限组列表 -->
          <div v-else class="groups-grid">
            <div v-for="g in groups" :key="g.id" class="group-card" :class="{ builtin: g.is_builtin }">
              <!-- 卡片头 -->
              <div class="gc-header">
                <div class="gc-title-row">
                  <span class="gc-name">{{ g.name }}</span>
                  <span v-if="g.is_builtin" class="badge badge-builtin">内置</span>
                </div>
                <div class="gc-meta">
                  <span class="gc-members">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="9" cy="7" r="4"/>
                      <path d="M2 21c0-4 3-7 7-7"/>
                      <path d="M14 10a4 4 0 1 0 0-8"/>
                      <path d="M22 21c0-4-3-7-7-7"/>
                    </svg>
                    {{ g.member_count }} 名成员
                  </span>
                </div>
              </div>

              <!-- 描述 -->
              <p class="gc-desc">{{ g.description || '暂无描述' }}</p>

              <!-- 权限标签 -->
              <div class="gc-perms">
                <span
                  v-for="perm in g.permissions"
                  :key="perm"
                  :class="['perm-tag', permTagClass(perm)]"
                >{{ perm }}</span>
                <span v-if="!g.permissions.length" class="perm-empty">无权限</span>
              </div>

              <!-- 操作按钮（仅 owner） -->
              <div v-if="isOwner" class="gc-actions">
                <button class="btn btn-xs btn-outline" @click="openEdit(g)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
                  编辑
                </button>
                <button
                  class="btn btn-xs btn-danger"
                  :disabled="g.is_builtin"
                  :title="g.is_builtin ? '内置组不可删除' : ''"
                  @click="confirmDelete(g)"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                  删除
                </button>
              </div>
            </div>
          </div>
        </section>

        <aside class="perm-catalog">
          <div class="pc-title">权限规划总览</div>
          <div class="pc-sub">右侧展示全部面板权限，便于分组时快速对照。</div>
          <div v-for="sec in PANEL_PERMISSION_PLAN" :key="sec.key" class="pc-section">
            <div class="pc-section-title">{{ sec.title }}</div>
            <div class="pc-items">
              <div v-for="p in sec.items" :key="p.value" class="pc-item">
                <div class="pc-item-main">
                  <span class="pc-item-label">{{ p.label }}</span>
                  <span :class="['perm-tag-sm', p.value.startsWith('panel.') ? 'tag-panel' : (p.value.startsWith('tshock.') ? 'tag-tshock' : 'tag-super')]">{{ p.value }}</span>
                </div>
                <div class="pc-item-desc">{{ p.desc }}</div>
              </div>
            </div>
          </div>
        </aside>
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

const form = ref({ name: '', description: '', permissions: [] })

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
  form.value = { name: '', description: '', permissions: [] }
  customPerm.value = ''
  formError.value = ''
  showModal.value = true
}

function openEdit(g) {
  editingGroup.value = g
  form.value = { name: g.name, description: g.description || '', permissions: [...g.permissions] }
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
        permissions: form.value.permissions,
      }
      if (!editingGroup.value.is_builtin) payload.name = name
      await updatePanelGroup(sid, editingGroup.value.id, payload)
    } else {
      await createPanelGroup(sid, {
        name,
        description: form.value.description,
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
.pg-page { display: flex; flex-direction: column; height: 100%; overflow: hidden; background: #f8fafc; }

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 28px 16px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 12px;
}
.page-title { font-size: 20px; font-weight: 700; color: #0f172a; margin: 0; }
.header-actions { display: flex; gap: 8px; }
.pg-body { flex: 1; overflow-y: auto; padding: 24px 28px; box-sizing: border-box; }

.empty-hint-box {
  text-align: center;
  padding: 60px 24px;
  color: #94a3b8;
}
.empty-icon {
  width: 40px;
  height: 40px;
  margin: 0 auto 12px;
  color: #94a3b8;
}
.empty-icon svg { width: 100%; height: 100%; }

.info-banner {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
  color: #1e40af;
  margin-bottom: 20px;
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
.info-icon svg { width: 100%; height: 100%; }

.pg-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
  align-items: start;
}

.pg-main { min-width: 0; }

.perm-catalog {
  position: sticky;
  top: 8px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
  max-height: calc(100vh - 180px);
  overflow: auto;
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

.loading-state { text-align: center; padding: 48px; color: #94a3b8; }

/* ── 权限组卡片网格 ── */
.groups-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.group-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,.05);
  transition: box-shadow .15s;
}
.group-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.08); }
.group-card.builtin { border-color: #c7d2fe; background: #fafafe; }

.gc-header { display: flex; align-items: flex-start; justify-content: space-between; }
.gc-title-row { display: flex; align-items: center; gap: 8px; }
.gc-name { font-size: 16px; font-weight: 700; color: #1e293b; }
.gc-meta { font-size: 12px; color: #94a3b8; }
.gc-members { display: inline-flex; align-items: center; gap: 4px; }
.gc-members svg { width: 13px; height: 13px; }

.badge { display: inline-block; padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-builtin { background: #e0e7ff; color: #4338ca; }

.gc-desc { font-size: 13px; color: #64748b; margin: 0; }

.gc-perms { display: flex; flex-wrap: wrap; gap: 6px; min-height: 24px; }
.perm-empty { font-size: 12px; color: #cbd5e1; }

.perm-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}
.tag-super { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
.tag-tshock { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.tag-panel { background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }
.tag-custom { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }

.gc-actions { display: flex; gap: 8px; padding-top: 4px; border-top: 1px solid #f1f5f9; }

/* ── 按钮 ── */
.btn { display: inline-flex; align-items: center; gap: 6px; border: none; cursor: pointer; border-radius: 6px; font-size: 13px; padding: 6px 14px; transition: .15s; }
.btn svg { width: 12px; height: 12px; }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn-primary { background: #6366f1; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #4f46e5; }
.btn-outline { background: transparent; border: 1px solid #cbd5e1; color: #475569; }
.btn-outline:hover:not(:disabled) { background: #f8fafc; }
.btn-danger { background: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; }
.btn-danger:hover:not(:disabled) { background: #fecaca; }
.btn-sm { padding: 5px 12px; }
.btn-xs { padding: 3px 10px; font-size: 12px; }

/* ── 模态框 ── */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.modal-box {
  background: #fff;
  border-radius: 14px;
  width: 560px;
  max-width: 95vw;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 48px rgba(0,0,0,.18);
}
.modal-sm { width: 400px; }
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px 0;
}
.modal-header h3 { font-size: 16px; font-weight: 700; color: #1e293b; margin: 0; }
.modal-close { background: none; border: none; font-size: 16px; cursor: pointer; color: #94a3b8; padding: 4px; }
.modal-body { padding: 16px 20px; }
.modal-footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid #f1f5f9;
}

.form-field { margin-bottom: 16px; }
.form-label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 6px; }
.required { color: #ef4444; }
.form-input {
  width: 100%; box-sizing: border-box;
  padding: 8px 12px; border: 1px solid #d1d5db;
  border-radius: 7px; font-size: 13px; color: #1e293b;
  outline: none; transition: border .15s;
}
.form-input:focus { border-color: #6366f1; }
.form-input:disabled { background: #f8fafc; color: #94a3b8; }
.form-error { color: #ef4444; font-size: 13px; text-align: center; padding: 0 20px 12px; }

/* ── 权限选择区 ── */
.perm-section {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 14px;
  max-height: 260px;
  overflow-y: auto;
}
.perm-group-title {
  font-size: 11px; font-weight: 700; color: #94a3b8;
  text-transform: uppercase; letter-spacing: .05em;
  margin: 10px 0 6px;
}
.perm-group-title:first-child { margin-top: 0; }
.perm-checks { display: flex; flex-direction: column; gap: 4px; }
.perm-check {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; color: #374151; cursor: pointer;
  padding: 3px 4px; border-radius: 4px;
}
.perm-check:hover { background: #f8fafc; }
.perm-check input { cursor: pointer; flex-shrink: 0; }
.perm-check-label { flex: 1; }
.perm-check-wild { border-top: 1px dashed #e2e8f0; margin-top: 4px; padding-top: 6px; }

.perm-tag-sm {
  padding: 1px 6px; border-radius: 4px; font-size: 11px; font-weight: 500;
}

/* ── 自定义权限 ── */
.custom-perm-row { display: flex; gap: 8px; }
.custom-perm-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.tag-remove {
  background: none; border: none; cursor: pointer;
  font-size: 13px; color: inherit; padding: 0 0 0 4px; line-height: 1;
}

@media (max-width: 1200px) {
  .pg-layout {
    grid-template-columns: 1fr;
  }

  .perm-catalog {
    position: static;
    max-height: none;
  }
}
</style>
