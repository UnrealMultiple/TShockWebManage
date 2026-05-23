<template>
  <div class="pa-page">
    <PageHeader title="平台权限组" subtitle="按权限组管理平台后台访问能力">
      <template #actions>
        <button class="pa-btn pa-btn-outline" :disabled="loading" @click="loadAll">
          {{ loading ? '刷新中' : '刷新' }}
        </button>
        <button class="pa-btn pa-btn-primary" @click="openCreate">新建权限组</button>
      </template>
    </PageHeader>

    <div class="pa-editor">
      <div v-if="toast.message" :class="['pa-toast', toast.type === 'ok' ? 'pa-toast-ok' : 'pa-toast-err']">
        {{ toast.message }}
        <button class="pa-toast-close" @click="clearToast">x</button>
      </div>

      <PlatformNav />

      <div class="pa-body">
        <section class="pa-section">
          <div class="pa-section-head">
            <span class="pa-section-title">权限组列表</span>
            <span class="pa-section-meta">已显示 {{ filteredGroups.length }} / {{ groups.length }} 项</span>
          </div>
          <div class="pa-subsection">
            <div class="pa-toolbar">
              <div class="pa-toolbar-left">
                <input v-model.trim="keyword" class="pa-input pa-search" placeholder="搜索组名、描述或权限" />
              </div>
              <div class="pa-toolbar-right">
                <button class="pa-btn pa-btn-outline" @click="keyword = ''">清空搜索</button>
                <button class="pa-btn pa-btn-primary" @click="openCreate">新建权限组</button>
              </div>
            </div>
          </div>

          <div class="pa-table-wrap">
            <table class="pa-table">
              <thead>
                <tr>
                  <th>组名</th>
                  <th>权限数量</th>
                  <th>成员数量</th>
                  <th>描述</th>
                  <th>权限预览</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="group in filteredGroups" :key="group.id">
                  <td>
                    <div class="pa-card-head">
                      <strong>{{ group.name }}</strong>
                      <span v-if="group.is_builtin" class="pa-badge pa-badge-blue">内置</span>
                    </div>
                  </td>
                  <td><span class="pa-badge pa-badge-gray">{{ permissionCount(group) }} 项</span></td>
                  <td>
                    <button class="pa-link-btn" @click="openMembers(group)">{{ group.member_count || 0 }} 名</button>
                  </td>
                  <td>{{ group.description || '暂无描述' }}</td>
                  <td>
                    <div class="pa-perm-preview">
                      <span
                        v-for="perm in previewPermissions(group)"
                        :key="perm"
                        :class="['pa-perm-chip', permChipClass(perm)]"
                      >
                        {{ perm }}
                      </span>
                      <span v-if="permissionCount(group) > 3" class="pa-meta">+{{ permissionCount(group) - 3 }}</span>
                      <span v-if="!permissionCount(group)" class="pa-meta">无权限</span>
                    </div>
                  </td>
                  <td>
                    <div class="pa-split-actions">
                      <button class="pa-btn pa-btn-sm pa-btn-outline" @click="openEdit(group)">编辑</button>
                      <button
                        class="pa-btn pa-btn-sm pa-btn-outline"
                        @click="openMembers(group)"
                      >
                        成员
                      </button>
                      <button
                        class="pa-btn pa-btn-sm pa-btn-danger"
                        :disabled="group.is_builtin"
                        @click="deleteGroup(group)"
                      >
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
                <tr v-if="!filteredGroups.length">
                  <td colspan="6" class="pa-empty-row">没有匹配的权限组</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>

    <div v-if="showEditor" class="modal-overlay" @click.self="closeEditor">
      <div class="modal-box">
        <div class="modal-header">
          <h3>{{ editingGroup ? '编辑权限组' : '新建权限组' }}</h3>
          <button class="modal-close" @click="closeEditor">×</button>
        </div>
        <div class="modal-body">
          <div class="form-field">
            <label class="form-label">组名 <span class="required">*</span></label>
            <input
              v-model.trim="form.name"
              class="form-input"
              placeholder="如 platform-admin"
            />
          </div>

          <div class="form-field">
            <label class="form-label">描述</label>
            <input
              v-model.trim="form.description"
              class="form-input"
              placeholder="权限组用途说明（可选）"
            />
          </div>

          <div class="form-field">
            <label class="form-label">权限</label>
            <div class="perm-section">
              <div v-for="section in permissionSections" :key="section.key">
                <template v-if="section.items.length">
                  <div class="perm-group-title">{{ section.title }}</div>
                  <div class="perm-checks">
                    <label v-for="perm in section.items" :key="perm.key" class="perm-check">
                      <input
                        v-model="form.permissions"
                        type="checkbox"
                        :value="perm.key"
                        :disabled="hasPlatformWildcard && perm.key !== '*'"
                      />
                      <span class="perm-check-label">{{ perm.label }}</span>
                      <span :class="['perm-tag-sm', permTagClass(perm.key)]">{{ perm.key }}</span>
                    </label>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <div class="form-field">
            <label class="form-label">追加自定义权限</label>
            <div class="custom-perm-row">
              <input
                v-model.trim="customPerm"
                class="form-input"
                placeholder="输入权限字符串后回车添加"
                :disabled="hasPlatformWildcard"
                @keydown.enter.prevent="addCustomPerm"
              />
              <button class="pa-btn pa-btn-outline" :disabled="hasPlatformWildcard" @click="addCustomPerm">
                添加
              </button>
            </div>
            <div v-if="customPerms.length" class="custom-perm-tags">
              <span v-for="perm in customPerms" :key="perm" class="perm-tag tag-custom">
                {{ perm }}
                <button class="tag-remove" @click="removeCustomPerm(perm)">×</button>
              </span>
            </div>
          </div>
        </div>
        <p v-if="formError" class="form-error">{{ formError }}</p>
        <div class="modal-footer">
          <button class="pa-btn pa-btn-outline" @click="closeEditor">取消</button>
          <button class="pa-btn pa-btn-primary" :disabled="saving" @click="saveGroup">
            {{ saving ? '保存中' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="membersGroup" class="modal-overlay" @click.self="closeMembers">
      <div class="modal-box">
        <div class="modal-header">
          <h3>组成员 - {{ membersGroup.name }}</h3>
          <button class="modal-close" @click="closeMembers">×</button>
        </div>
        <div class="modal-body">
          <div class="member-add-row">
            <input v-model.trim="memberUserId" class="form-input" placeholder="输入用户 ID" />
            <button class="pa-btn pa-btn-primary" @click="addMember">加入权限组</button>
          </div>
          <table v-if="members.length" class="member-list-table">
            <thead>
              <tr>
                <th>邮箱</th>
                <th>用户 ID</th>
                <th>加入时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="member in members" :key="member.user_id">
                <td>{{ member.email }}</td>
                <td>{{ member.user_id }}</td>
                <td>{{ fmtTime(member.assigned_at) }}</td>
                <td>
                  <button class="pa-btn pa-btn-sm pa-btn-danger" @click="removeMember(member.user_id)">
                    移出
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-row">
            该权限组暂无成员
          </div>
        </div>
        <div class="modal-footer">
          <button class="pa-btn pa-btn-outline" @click="closeMembers">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import PlatformNav from '@/components/PlatformNav.vue'
import PageHeader from '@/components/PageHeader.vue'
import {
  addPlatformPermissionGroupMember,
  createPlatformPermissionGroup,
  deletePlatformPermissionGroup,
  listPlatformPermissionGroupMembers,
  listPlatformPermissionGroups,
  listPlatformPermissions,
  removePlatformPermissionGroupMember,
  updatePlatformPermissionGroup,
} from '@/api/platform'
import './platform-admin.css'

const loading = ref(false)
const saving = ref(false)
const groups = ref([])
const catalog = ref([])
const keyword = ref('')
const toast = reactive({ message: '', type: 'ok' })

const showEditor = ref(false)
const editingGroup = ref(null)
const form = reactive({ name: '', description: '', permissions: [] })
const formError = ref('')
const customPerm = ref('')

const membersGroup = ref(null)
const members = ref([])
const memberUserId = ref('')

const hasPlatformWildcard = computed(() => form.permissions.includes('*'))

const knownPlatformPerms = computed(() => {
  const keys = new Set(['*'])
  for (const perm of catalog.value || []) {
    if (perm?.key) keys.add(perm.key)
  }
  return keys
})

const customPerms = computed(() => form.permissions.filter((perm) => !knownPlatformPerms.value.has(perm)))

const permissionSections = computed(() => [
  {
    key: 'admin',
    title: '超级权限',
    items: [{ key: '*', label: '全部平台权限' }],
  },
  {
    key: 'dashboard',
    title: '总览与服务器',
    items: catalog.value.filter((p) => p.key.includes('dashboard') || p.key.includes('servers')),
  },
  {
    key: 'account',
    title: '账号与权限',
    items: catalog.value.filter((p) => p.key.includes('accounts') || p.key.includes('rbac')),
  },
  {
    key: 'operation',
    title: '运营与日志',
    items: catalog.value.filter((p) => p.key.includes('announcements') || p.key.includes('logs') || p.key.includes('settings') || p.key.includes('reports')),
  },
])

const filteredGroups = computed(() => {
  const key = keyword.value.toLowerCase()
  if (!key) return groups.value
  return groups.value.filter((group) => {
    const perms = (group.permissions || []).join(' ').toLowerCase()
    return (group.name || '').toLowerCase().includes(key)
      || (group.description || '').toLowerCase().includes(key)
      || perms.includes(key)
  })
})

function showToast(message, type = 'ok') {
  toast.message = message
  toast.type = type
}

function clearToast() {
  toast.message = ''
}

function fmtTime(ts) {
  if (!ts || typeof ts !== 'number') return '-'
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

function permissionCount(group) {
  return (group.permissions || []).length
}

function previewPermissions(group) {
  return (group.permissions || []).slice(0, 3)
}

function permChipClass(perm) {
  if (perm === '*') return 'is-super'
  if (perm.includes('servers')) return 'is-server'
  if (perm.includes('accounts') || perm.includes('rbac')) return 'is-account'
  return 'is-platform'
}

function permTagClass(perm) {
  if (perm === '*') return 'tag-super'
  if (perm.includes('servers')) return 'tag-server'
  if (perm.includes('accounts') || perm.includes('rbac')) return 'tag-account'
  return 'tag-platform'
}

function addCustomPerm() {
  const value = customPerm.value.trim()
  if (value && !form.permissions.includes(value) && !hasPlatformWildcard.value) {
    form.permissions.push(value)
  }
  customPerm.value = ''
}

function removeCustomPerm(perm) {
  form.permissions = form.permissions.filter((item) => item !== perm)
}

async function loadAll() {
  loading.value = true
  clearToast()
  try {
    const [groupData, permissionData] = await Promise.all([
      listPlatformPermissionGroups(),
      listPlatformPermissions(),
    ])
    groups.value = groupData || []
    catalog.value = permissionData || []
  } catch (e) {
    showToast(e.message || '加载平台权限组失败', 'err')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingGroup.value = null
  Object.assign(form, { name: '', description: '', permissions: [] })
  customPerm.value = ''
  formError.value = ''
  showEditor.value = true
}

function openEdit(group) {
  editingGroup.value = group
  Object.assign(form, {
    name: group.name,
    description: group.description || '',
    permissions: [...(group.permissions || [])],
  })
  customPerm.value = ''
  formError.value = ''
  showEditor.value = true
}

function closeEditor() {
  showEditor.value = false
  editingGroup.value = null
  customPerm.value = ''
  formError.value = ''
}

async function saveGroup() {
  formError.value = ''
  if (!form.name) {
    formError.value = '组名不能为空'
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name,
      description: form.description,
      permissions: [...new Set(form.permissions)],
    }
    if (editingGroup.value) await updatePlatformPermissionGroup(editingGroup.value.id, payload)
    else await createPlatformPermissionGroup(payload)
    showToast('平台权限组已保存')
    closeEditor()
    await loadAll()
  } catch (e) {
    showToast(e.message || '保存平台权限组失败', 'err')
  } finally {
    saving.value = false
  }
}

async function deleteGroup(group) {
  if (group.is_builtin) return
  try {
    await deletePlatformPermissionGroup(group.id)
    showToast('平台权限组已删除')
    await loadAll()
  } catch (e) {
    showToast(e.message || '删除平台权限组失败', 'err')
  }
}

async function openMembers(group) {
  membersGroup.value = group
  memberUserId.value = ''
  try {
    members.value = await listPlatformPermissionGroupMembers(group.id)
  } catch (e) {
    showToast(e.message || '加载组成员失败', 'err')
  }
}

function closeMembers() {
  membersGroup.value = null
  members.value = []
}

async function addMember() {
  if (!membersGroup.value || !memberUserId.value) return
  try {
    await addPlatformPermissionGroupMember(membersGroup.value.id, Number(memberUserId.value))
    memberUserId.value = ''
    await openMembers(membersGroup.value)
    await loadAll()
    showToast('成员已加入权限组')
  } catch (e) {
    showToast(e.message || '加入成员失败', 'err')
  }
}

async function removeMember(userId) {
  if (!membersGroup.value) return
  try {
    await removePlatformPermissionGroupMember(membersGroup.value.id, userId)
    await openMembers(membersGroup.value)
    await loadAll()
    showToast('成员已移出权限组')
  } catch (e) {
    showToast(e.message || '移出成员失败', 'err')
  }
}

onMounted(loadAll)
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(2px);
  animation: fade-in 0.2s ease-out;
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-box {
  width: 560px;
  max-width: 95vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.25);
  animation: slide-up 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slide-up {
  from { transform: translateY(12px); opacity: 0; }
  to { transform: none; opacity: 1; }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h3 {
  margin: 0;
  color: #1e293b;
  font-size: 16px;
  font-weight: 700;
}

.modal-close {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  border: none;
  border-radius: 50%;
  background: #f1f5f9;
  color: #64748b;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  transition: all 0.2s;
}

.modal-close:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 20px;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
}

.form-field {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  margin-bottom: 6px;
  color: #334155;
  font-size: 13px;
  font-weight: 600;
}

.required {
  color: #ef4444;
}

.form-input {
  width: 100%;
  box-sizing: border-box;
  padding: 9px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  outline: none;
  background: #fff;
  color: #0f172a;
  font-size: 13px;
  transition: all 0.2s;
  box-shadow: inset 0 1px 2px rgb(0 0 0 / 0.02);
}

.form-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.form-input:disabled {
  background: #f8fafc;
  color: #94a3b8;
}

.form-error {
  margin: 0;
  padding: 0 20px 12px;
  color: #ef4444;
  font-size: 13px;
  text-align: center;
}

.perm-section {
  max-height: 260px;
  overflow-y: auto;
  padding: 12px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
}

.perm-group-title {
  margin: 10px 0 6px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.perm-group-title:first-child {
  margin-top: 0;
}

.perm-checks {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.perm-check {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
  border-radius: 6px;
  color: #374151;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}

.perm-check:hover {
  background: #f8fafc;
}

.perm-check input {
  flex-shrink: 0;
  cursor: pointer;
}

.perm-check-label {
  flex: 1;
  min-width: 0;
}

.perm-tag,
.perm-tag-sm {
  display: inline-flex;
  align-items: center;
  border: 1px solid transparent;
  font-weight: 500;
  white-space: nowrap;
}

.perm-tag {
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 12px;
}

.perm-tag-sm {
  max-width: 210px;
  overflow: hidden;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  text-overflow: ellipsis;
}

.tag-super {
  background: #fef3c7;
  color: #92400e;
  border-color: #fde68a;
}

.tag-server {
  background: #dbeafe;
  color: #1e40af;
  border-color: #bfdbfe;
}

.tag-account {
  background: #f3e8ff;
  color: #6d28d9;
  border-color: #ddd6fe;
}

.tag-platform,
.tag-custom {
  background: #f1f5f9;
  color: #475569;
  border-color: #e2e8f0;
}

.custom-perm-row,
.member-add-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.custom-perm-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.tag-remove {
  padding: 0 0 0 4px;
  border: none;
  background: none;
  color: inherit;
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
}

.member-list-table {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  border-collapse: separate;
  border-spacing: 0;
  overflow: hidden;
}

.member-list-table th,
.member-list-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #f1f5f9;
  text-align: left;
  font-size: 13px;
}

.member-list-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
}

.member-list-table tr:last-child td {
  border-bottom: none;
}

.empty-row {
  padding: 24px;
  color: #94a3b8;
  text-align: center;
  font-size: 14px;
}

@media (max-width: 768px) {
  .modal-overlay {
    align-items: stretch;
    padding: 12px;
  }

  .modal-box {
    max-height: calc(100vh - 24px);
  }

  .custom-perm-row,
  .member-add-row {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
