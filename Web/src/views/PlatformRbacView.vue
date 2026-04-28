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

    <div v-if="showEditor" class="pa-modal-overlay" @click.self="closeEditor">
      <div class="pa-modal">
        <div class="pa-modal-head">
          <h3>{{ editingGroup ? '编辑权限组' : '新建权限组' }}</h3>
          <button class="pa-toast-close" @click="closeEditor">x</button>
        </div>
        <div class="pa-modal-body">
          <div class="pa-form-grid">
            <input v-model.trim="form.name" class="pa-input" placeholder="权限组名称" />
            <input v-model.trim="form.description" class="pa-input" placeholder="权限组描述" />
          </div>

          <div class="pa-perm-editor">
            <section v-for="section in permissionSections" :key="section.key" class="pa-perm-section">
              <div class="pa-subsection-label">{{ section.title }}</div>
              <div class="pa-perm-grid">
                <label v-for="perm in section.items" :key="perm.key" class="pa-perm-card">
                  <input
                    v-model="form.permissions"
                    type="checkbox"
                    :value="perm.key"
                    :disabled="form.permissions.includes('*') && perm.key !== '*'"
                  />
                  <span>
                    <span class="pa-perm-name">{{ perm.label }}</span>
                    <span class="pa-perm-key">{{ perm.key }}</span>
                  </span>
                </label>
              </div>
            </section>
          </div>
        </div>
        <div class="pa-modal-foot">
          <button class="pa-btn pa-btn-outline" @click="closeEditor">取消</button>
          <button class="pa-btn pa-btn-primary" :disabled="saving" @click="saveGroup">
            {{ saving ? '保存中' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="membersGroup" class="pa-modal-overlay" @click.self="closeMembers">
      <div class="pa-modal">
        <div class="pa-modal-head">
          <h3>组成员 - {{ membersGroup.name }}</h3>
          <button class="pa-toast-close" @click="closeMembers">x</button>
        </div>
        <div class="pa-modal-body">
          <div class="pa-inline-form">
            <input v-model.trim="memberUserId" class="pa-input pa-filter" placeholder="用户 ID" />
            <button class="pa-btn pa-btn-primary" @click="addMember">加入权限组</button>
          </div>
          <div class="pa-list pa-members-list">
            <article v-for="member in members" :key="member.user_id" class="pa-list-card">
              <div class="pa-list-main">
                <strong>{{ member.email }}</strong>
                <span class="pa-meta">用户 ID：{{ member.user_id }} · 加入于 {{ fmtTime(member.assigned_at) }}</span>
              </div>
              <button class="pa-btn pa-btn-sm pa-btn-danger" @click="removeMember(member.user_id)">移出</button>
            </article>
            <div v-if="!members.length" class="pa-empty">该权限组暂无成员</div>
          </div>
        </div>
        <div class="pa-modal-foot">
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

const membersGroup = ref(null)
const members = ref([])
const memberUserId = ref('')

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
  showEditor.value = true
}

function openEdit(group) {
  editingGroup.value = group
  Object.assign(form, {
    name: group.name,
    description: group.description || '',
    permissions: [...(group.permissions || [])],
  })
  showEditor.value = true
}

function closeEditor() {
  showEditor.value = false
  editingGroup.value = null
}

async function saveGroup() {
  if (!form.name) return
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
