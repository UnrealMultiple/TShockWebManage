<template>
  <div class="pa-page">
    <PageHeader title="账号管理" subtitle="查看账号、所属服务器与平台处置">
      <template #actions>
        <button class="pa-btn pa-btn-outline" :disabled="loading" @click="loadAll">
          {{ loading ? '刷新中' : '刷新' }}
        </button>
      </template>
    </PageHeader>

    <div class="pa-editor">
      <div v-if="toast.message" :class="['pa-toast', toast.type === 'ok' ? 'pa-toast-ok' : 'pa-toast-err']">
        {{ toast.message }}
        <button class="pa-toast-close" @click="clearToast">x</button>
      </div>

      <PlatformNav />

      <div class="pa-body">
        <div>
          <section class="pa-section">
            <div class="pa-section-head">
              <span class="pa-section-title">账号列表</span>
              <span class="pa-section-meta">共 {{ pagination.total }} 个账号</span>
            </div>

            <div class="pa-subsection">
              <div class="pa-toolbar">
                <div class="pa-toolbar-left">
                  <select v-model="filters.status" class="pa-input pa-filter">
                    <option value="">全部账号</option>
                    <option value="normal">正常账号</option>
                    <option value="banned">已封禁</option>
                  </select>
                  <input
                    v-model.trim="filters.q"
                    class="pa-input pa-search"
                    placeholder="搜索账号编号或邮箱关键词"
                    @keyup.enter="applyFilters"
                  />
                </div>
                <div class="pa-toolbar-right">
                  <select v-model.number="pagination.limit" class="pa-input pa-filter" @change="applyFilters">
                    <option :value="10">每页 10 条</option>
                    <option :value="20">每页 20 条</option>
                    <option :value="50">每页 50 条</option>
                  </select>
                  <button class="pa-btn pa-btn-outline" @click="applyFilters">筛选</button>
                  <button class="pa-btn pa-btn-outline" @click="resetFilters">重置</button>
                </div>
              </div>
            </div>

            <div class="pa-table-wrap">
              <table class="pa-table">
                <thead>
                  <tr>
                    <th>账号</th>
                    <th>状态</th>
                    <th>平台权限</th>
                    <th>服务器</th>
                    <th>限制</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="account in accounts"
                    :key="account.id"
                    :class="{ 'pa-table-row-active': selectedUserId === account.id }"
                  >
                    <td>
                      <strong>{{ account.email }}</strong>
                      <div class="pa-table-meta">用户 ID：{{ account.id }} · 注册于 {{ fmtTime(account.created_at) }}</div>
                    </td>
                    <td>
                      <span :class="['pa-badge', account.is_banned ? 'pa-badge-red' : 'pa-badge-green']">
                        {{ account.is_banned ? '已封禁' : '正常' }}
                      </span>
                    </td>
                    <td>
                      <div class="pa-inline-badges">
                        <span
                          v-for="name in displayPlatformGroupNames(account).slice(0, 2)"
                          :key="name"
                          class="pa-badge pa-badge-gray"
                        >
                          {{ name }}
                        </span>
                        <span v-if="displayPlatformGroupNames(account).length > 2" class="pa-meta">+{{ displayPlatformGroupNames(account).length - 2 }}</span>
                      </div>
                    </td>
                    <td>{{ account.server_count }} 个参与 / {{ account.owned_server_count }} 个拥有</td>
                    <td>{{ account.active_restrictions_count || 0 }}</td>
                    <td>
                      <div class="pa-split-actions">
                        <button class="pa-btn pa-btn-sm pa-btn-outline" @click="showAccountDetail(account.id)">详情</button>
                        <button
                          v-if="!account.is_banned"
                          class="pa-btn pa-btn-sm pa-btn-danger"
                          @click="prepareAccountAction('ban', account)"
                        >
                          封禁
                        </button>
                        <button
                          v-else
                          class="pa-btn pa-btn-sm pa-btn-outline"
                          @click="unbanAccount(account.id)"
                        >
                          解封
                        </button>
                      </div>
                    </td>
                  </tr>
                  <tr v-if="!accounts.length">
                    <td colspan="6" class="pa-empty-row">暂无账号</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="pa-pagination">
              <button class="pa-btn pa-btn-sm pa-btn-outline" :disabled="pagination.page <= 1 || loading" @click="goPage(pagination.page - 1)">
                上一页
              </button>
              <span class="pa-meta">第 {{ pagination.page }} / {{ totalPages }} 页</span>
              <button class="pa-btn pa-btn-sm pa-btn-outline" :disabled="pagination.page >= totalPages || loading" @click="goPage(pagination.page + 1)">
                下一页
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>

    <div v-if="accountDetail" class="pa-modal-overlay pa-detail-overlay" @click.self="closeAccountDetail">
      <div class="pa-modal pa-detail-modal">
        <div class="pa-modal-head">
          <div class="pa-modal-title-block">
            <h3>账号详情与操作</h3>
            <span class="pa-section-meta">用户 ID：{{ accountDetail.user.id }} · 注册于 {{ fmtTime(accountDetail.user.created_at) }}</span>
          </div>
          <button class="pa-modal-close" @click="closeAccountDetail">x</button>
        </div>
        <div class="pa-modal-body">
          <div class="pa-drawer-profile pa-account-profile" :class="{ 'is-banned': accountDetail.user.is_banned }">
            <div class="pa-account-avatar">{{ accountInitial(accountDetail.user.email) }}</div>
            <div class="pa-account-main">
              <div class="pa-account-title-row">
                <strong>{{ accountDetail.user.email }}</strong>
                <span :class="['pa-badge', accountDetail.user.is_banned ? 'pa-badge-red' : 'pa-badge-green']">
                  {{ accountDetail.user.is_banned ? '已封禁' : '正常' }}
                </span>
              </div>
              <div class="pa-meta">{{ accountDetailGroupLabel }}</div>
            </div>
          </div>

          <div class="pa-account-metrics">
            <div class="pa-metric-tile">
              <span>拥有服务器</span>
              <strong>{{ accountDetail.user.owned_server_count }}</strong>
            </div>
            <div class="pa-metric-tile">
              <span>参与服务器</span>
              <strong>{{ accountDetail.user.server_count }}</strong>
            </div>
            <div class="pa-metric-tile">
              <span>生效限制</span>
              <strong>{{ accountDetail.restrictions.length }}</strong>
            </div>
          </div>

          <div class="pa-drawer-sections">
            <section class="pa-modal-card">
              <div class="pa-account-list-head">
                <span class="pa-subsection-label">拥有的服务器</span>
                <span class="pa-meta">{{ ownedServers.length }} 项</span>
              </div>
              <div class="pa-list pa-modal-scroll-list">
                <article v-for="server in ownedServers" :key="server.server_id" class="pa-list-card pa-server-mini-card">
                  <div class="pa-list-main">
                    <div class="pa-card-head">
                      <strong>{{ server.server_name }}</strong>
                      <span class="pa-badge pa-badge-blue">服主</span>
                    </div>
                    <div class="pa-meta">
                      #{{ server.server_id }} · {{ server.server_code || '-' }} · {{ platformStatusLabel(server.platform_status) }}
                    </div>
                  </div>
                </article>
                <div v-if="!ownedServers.length" class="pa-empty">该账号暂未拥有服务器</div>
              </div>
            </section>

            <section class="pa-modal-card">
              <div class="pa-account-list-head">
                <span class="pa-subsection-label">参与的服务器</span>
                <span class="pa-meta">{{ joinedServers.length }} 项</span>
              </div>
              <div class="pa-list pa-modal-scroll-list">
                <article
                  v-for="server in joinedServers"
                  :key="server.server_id"
                  class="pa-list-card pa-server-mini-card"
                >
                  <div class="pa-list-main">
                    <div class="pa-card-head">
                      <strong>{{ server.server_name }}</strong>
                      <span class="pa-badge pa-badge-gray">{{ roleLabel(server.role) }}</span>
                    </div>
                    <div class="pa-meta">
                      #{{ server.server_id }} · {{ server.server_code || '-' }} · {{ platformStatusLabel(server.platform_status) }}
                    </div>
                  </div>
                  <button
                    class="pa-btn pa-btn-sm pa-btn-outline"
                    :disabled="actionBusy"
                    @click="prepareServerAction(server)"
                  >
                    移出
                  </button>
                  <div
                    v-if="actionDraft.kind === 'removeMember' && actionDraft.server_id === server.server_id"
                    class="pa-inline-action-form"
                  >
                    <div class="pa-action-context">
                      <strong>{{ actionLabel(actionDraft.kind) }}</strong>
                      <span>目标服务器：{{ actionDraft.server_name }}</span>
                    </div>
                    <textarea
                      v-model.trim="actionDraft.reason"
                      class="pa-input"
                      rows="3"
                      :placeholder="actionPlaceholder(actionDraft.kind)"
                    ></textarea>
                    <div class="pa-split-actions">
                      <button class="pa-btn pa-btn-primary" :disabled="actionBusy" @click="submitDraftAction">
                        {{ actionBusy ? '执行中' : '确认执行' }}
                      </button>
                      <button class="pa-btn pa-btn-outline" :disabled="actionBusy" @click="resetDraftAction">
                        取消
                      </button>
                    </div>
                  </div>
                </article>
                <div v-if="!joinedServers.length" class="pa-empty">该账号暂未参与其他服务器</div>
              </div>
            </section>

            <section class="pa-modal-card">
              <div class="pa-account-list-head">
                <span class="pa-subsection-label">平台权限组</span>
                <span class="pa-meta">{{ accountDetailGroupLabel }}</span>
              </div>
              <div class="pa-permission-assign-row">
                <select v-model="assigningGroupId" class="pa-input">
                  <option value="">选择权限组</option>
                  <option
                    v-for="group in availablePlatformGroups"
                    :key="group.id"
                    :value="String(group.id)"
                  >
                    {{ group.name }}
                  </option>
                </select>
                <button
                  class="pa-btn pa-btn-primary"
                  :disabled="!assigningGroupId || permissionBusy"
                  @click="assignPlatformGroup"
                >
                  分配
                </button>
              </div>
              <div class="pa-list pa-modal-scroll-list is-short">
                <article v-for="group in assignedPlatformGroups" :key="group.id" class="pa-list-card pa-permission-group-card">
                  <div class="pa-list-main">
                    <div class="pa-card-head">
                      <strong>{{ group.name }}</strong>
                      <span v-if="group.is_builtin" class="pa-badge pa-badge-blue">内置</span>
                    </div>
                    <div class="pa-meta">{{ group.permissions?.length || 0 }} 项权限 · 加入于 {{ fmtTime(group.assigned_at) }}</div>
                  </div>
                  <button
                    class="pa-btn pa-btn-sm pa-btn-danger"
                    :disabled="permissionBusy"
                    @click="removePlatformGroup(group.id)"
                  >
                    移出
                  </button>
                </article>
                <div v-if="!assignedPlatformGroups.length" class="pa-empty">当前权限组：成员</div>
              </div>
            </section>

            <section class="pa-modal-card">
              <div class="pa-account-list-head">
                <span class="pa-subsection-label">生效中的限制</span>
                <span class="pa-meta">{{ accountDetail.restrictions.length }} 项</span>
              </div>
              <div class="pa-list pa-modal-scroll-list">
                <article v-for="item in accountDetail.restrictions" :key="item.id" class="pa-list-card pa-restriction-card">
                  <div class="pa-list-main">
                    <div class="pa-card-head">
                      <span :class="['pa-badge', restrictionBadge(item.restriction_type)]">
                        {{ restrictionLabel(item.restriction_type) }}
                      </span>
                      <span class="pa-meta">{{ fmtTime(item.created_at) }}</span>
                    </div>
                    <div class="pa-meta">{{ item.reason || '无原因' }}</div>
                  </div>
                </article>
                <div v-if="!accountDetail.restrictions.length" class="pa-empty">暂无账号限制</div>
              </div>
            </section>

            <section class="pa-modal-card pa-modal-card-danger">
              <div class="pa-account-action-head">
                <div>
                  <span class="pa-subsection-label">平台处置</span>
                  <div class="pa-meta">{{ accountDetail.user.is_banned ? '已封禁' : '正常' }}</div>
                </div>
                <button
                  v-if="!actionDraft.kind && !accountDetail.user.is_banned"
                  class="pa-btn pa-btn-sm pa-btn-danger"
                  @click="prepareAccountAction('ban', accountDetail.user)"
                >
                  封禁账号
                </button>
                <button
                  v-if="!actionDraft.kind && accountDetail.user.is_banned"
                  class="pa-btn pa-btn-sm pa-btn-outline"
                  @click="unbanAccount(accountDetail.user.id)"
                >
                  解除封禁
                </button>
              </div>
              <div v-if="actionDraft.kind === 'ban'" class="pa-form-grid">
                <div class="pa-action-context">
                  <strong>{{ actionLabel(actionDraft.kind) }}</strong>
                  <span v-if="actionDraft.server_name">目标服务器：{{ actionDraft.server_name }}</span>
                  <span v-else>目标账号：{{ actionDraft.email }}</span>
                </div>
                <textarea
                  v-model.trim="actionDraft.reason"
                  class="pa-input"
                  rows="4"
                  :placeholder="actionPlaceholder(actionDraft.kind)"
                ></textarea>
                <div class="pa-split-actions">
                  <button class="pa-btn pa-btn-primary" :disabled="actionBusy" @click="submitDraftAction">
                    {{ actionBusy ? '执行中' : '确认执行' }}
                  </button>
                  <button class="pa-btn pa-btn-outline" :disabled="actionBusy" @click="resetDraftAction">取消</button>
                </div>
              </div>
            </section>
          </div>
        </div>
        <div class="pa-modal-foot">
          <button class="pa-btn pa-btn-outline" @click="closeAccountDetail">关闭</button>
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
  banPlatformAccount,
  getPlatformAccountDetail,
  listPlatformPermissionGroups,
  listPlatformAccounts,
  removePlatformAccountFromServer,
  removePlatformPermissionGroupMember,
  unbanPlatformAccount,
} from '@/api/platform'
import './platform-admin.css'

const loading = ref(false)
const accounts = ref([])
const accountDetail = ref(null)
const permissionGroups = ref([])
const assigningGroupId = ref('')
const permissionBusy = ref(false)
const actionBusy = ref(false)
const selectedUserId = ref(null)
const filters = reactive({ q: '', status: '' })
const pagination = reactive({ page: 1, limit: 20, total: 0 })
const toast = reactive({ message: '', type: 'ok' })
const actionDraft = reactive({
  kind: '',
  user_id: null,
  email: '',
  server_id: null,
  server_name: '',
  reason: '',
})
const totalPages = computed(() => Math.max(1, Math.ceil((pagination.total || 0) / pagination.limit)))
const ownedServers = computed(() => accountDetail.value?.servers?.filter((server) => server.is_owner) || [])
const joinedServers = computed(() => accountDetail.value?.servers?.filter((server) => !server.is_owner) || [])
const assignedPlatformGroups = computed(() => accountDetail.value?.platform_groups || [])
const assignedPlatformGroupIds = computed(() => new Set(assignedPlatformGroups.value.map((group) => Number(group.id))))
const availablePlatformGroups = computed(() =>
  permissionGroups.value.filter((group) => !assignedPlatformGroupIds.value.has(Number(group.id)))
)
const accountDetailGroupLabel = computed(() => {
  const names = assignedPlatformGroups.value.map((group) => group.name).filter(Boolean)
  return names.length ? names.join(' / ') : '成员'
})

function showToast(message, type = 'ok') {
  toast.message = message
  toast.type = type
}

function clearToast() {
  toast.message = ''
}

function s(v) { return v == null ? '' : (typeof v === 'string' ? v : String(v)) }

function fmtTime(ts) {
  if (!ts || typeof ts !== 'number') return '-'
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

function accountInitial(email) {
  return String(email || '?').trim().slice(0, 1).toUpperCase()
}

function displayPlatformGroupNames(account) {
  const names = (account?.platform_group_names || []).map(function(n) { return typeof n === 'string' ? n : (n?.name || String(n)) })
  return names.length ? names : ['成员']
}

function roleLabel(role) {
  const r = typeof role === 'object' && role ? (role.value || role.name || String(role)) : role
  return ({ owner: '服主', web_staff: '管理成员', member: '普通成员' })[r] || s(r) || '-'
}

function platformStatusLabel(status) {
  return ({ active: '运行中', inactive: '未启用', suspended: '已下架' })[s(status)] || s(status) || '-'
}

function restrictionLabel(type) {
  return ({ ban: '全站封禁', qq_limit: 'QQ 限制', role_limit: '角色限制' })[s(type)] || s(type)
}

function restrictionBadge(type) {
  return ({ ban: 'pa-badge-red', qq_limit: 'pa-badge-yellow', role_limit: 'pa-badge-blue' })[s(type)] || 'pa-badge-gray'
}

function actionLabel(kind) {
  return ({ ban: '封禁账号', removeMember: '从服务器移出' })[s(kind)] || '账号操作'
}

function actionPlaceholder(kind) {
  return ({
    ban: '填写封禁原因，账号将无法继续登录和使用平台',
    removeMember: '填写移出原因，平台会记录本次操作',
  })[s(kind)] || '填写操作原因'
}

function queryParams() {
  return {
    q: filters.q,
    status: filters.status,
    skip: (pagination.page - 1) * pagination.limit,
    limit: pagination.limit,
  }
}

async function loadAccounts() {
  loading.value = true
  clearToast()
  try {
    const data = await listPlatformAccounts(queryParams())
    accounts.value = data.items || []
    pagination.total = data.total || 0
    if (pagination.page > totalPages.value) {
      pagination.page = totalPages.value
      await loadAccounts()
    }
  } catch (e) {
    showToast(e.message || '加载账号列表失败', 'err')
  } finally {
    loading.value = false
  }
}

async function loadPermissionGroups() {
  try {
    permissionGroups.value = await listPlatformPermissionGroups()
  } catch (e) {
    showToast(e.message || '加载平台权限组失败', 'err')
  }
}

async function showAccountDetail(userId, resetAction = true) {
  try {
    selectedUserId.value = userId
    if (!permissionGroups.value.length) await loadPermissionGroups()
    accountDetail.value = await getPlatformAccountDetail(userId)
    if (resetAction) resetDraftAction()
  } catch (e) {
    showToast(e.message || '加载账号详情失败', 'err')
  }
}

function closeAccountDetail() {
  accountDetail.value = null
  selectedUserId.value = null
  resetDraftAction()
}

async function loadAll() {
  await Promise.all([loadAccounts(), loadPermissionGroups()])
  if (selectedUserId.value) await showAccountDetail(selectedUserId.value)
}

function applyFilters() {
  pagination.page = 1
  loadAccounts()
}

function resetFilters() {
  filters.q = ''
  filters.status = ''
  pagination.page = 1
  loadAccounts()
}

function goPage(page) {
  pagination.page = Math.min(Math.max(1, page), totalPages.value)
  loadAccounts()
}

function prepareAccountAction(kind, account) {
  actionDraft.kind = kind
  actionDraft.user_id = account.id
  actionDraft.email = account.email
  actionDraft.server_id = null
  actionDraft.server_name = ''
  actionDraft.reason = ''
  if (!accountDetail.value || accountDetail.value.user.id !== account.id) showAccountDetail(account.id, false)
}

function prepareServerAction(server) {
  if (!accountDetail.value) return
  actionDraft.kind = 'removeMember'
  actionDraft.user_id = accountDetail.value.user.id
  actionDraft.email = accountDetail.value.user.email
  actionDraft.server_id = server.server_id
  actionDraft.server_name = server.server_name
  actionDraft.reason = ''
}

function resetDraftAction() {
  Object.assign(actionDraft, {
    kind: '',
    user_id: null,
    email: '',
    server_id: null,
    server_name: '',
    reason: '',
  })
}

async function submitDraftAction() {
  if (!actionDraft.kind || !actionDraft.user_id) return
  if (actionDraft.kind === 'removeMember' && !actionDraft.server_id) {
    showToast('移出操作缺少目标服务器', 'err')
    return
  }
  if (!actionDraft.reason) {
    showToast('请填写操作原因', 'err')
    return
  }
  const userId = actionDraft.user_id
  actionBusy.value = true
  try {
    if (actionDraft.kind === 'ban') {
      await banPlatformAccount(userId, actionDraft.reason)
      showToast('账号已封禁')
    } else if (actionDraft.kind === 'removeMember') {
      await removePlatformAccountFromServer(userId, actionDraft.server_id, actionDraft.reason)
      showToast('账号已从服务器移出')
    }
    resetDraftAction()
    await loadAccounts()
    await showAccountDetail(userId)
  } catch (e) {
    showToast(e.message || '执行账号操作失败', 'err')
  } finally {
    actionBusy.value = false
  }
}

async function unbanAccount(userId) {
  const detailOpen = accountDetail.value?.user?.id === userId
  try {
    await unbanPlatformAccount(userId, '平台解除封禁')
    showToast('账号已解封')
    await loadAccounts()
    if (detailOpen) await showAccountDetail(userId)
  } catch (e) {
    showToast(e.message || '解除封禁失败', 'err')
  }
}

async function assignPlatformGroup() {
  const userId = accountDetail.value?.user?.id
  const groupId = Number(assigningGroupId.value)
  if (!userId || !groupId) return
  permissionBusy.value = true
  try {
    await addPlatformPermissionGroupMember(groupId, userId)
    assigningGroupId.value = ''
    showToast('平台权限组已分配')
    await loadPermissionGroups()
    await loadAccounts()
    await showAccountDetail(userId, false)
  } catch (e) {
    showToast(e.message || '分配平台权限组失败', 'err')
  } finally {
    permissionBusy.value = false
  }
}

async function removePlatformGroup(groupId) {
  const userId = accountDetail.value?.user?.id
  if (!userId || !groupId) return
  permissionBusy.value = true
  try {
    await removePlatformPermissionGroupMember(groupId, userId)
    showToast('平台权限组已移出')
    await loadPermissionGroups()
    await loadAccounts()
    await showAccountDetail(userId, false)
  } catch (e) {
    showToast(e.message || '移出平台权限组失败', 'err')
  } finally {
    permissionBusy.value = false
  }
}

onMounted(loadAll)
</script>
