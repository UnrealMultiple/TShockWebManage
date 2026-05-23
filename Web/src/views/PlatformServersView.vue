<template>
  <div class="pa-page">
    <PageHeader title="服务器管理" subtitle="审核新服务器、管理展示状态与平台处置">
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
              <span class="pa-section-title">服务器列表</span>
              <span class="pa-section-meta">共 {{ pagination.total }} 项，本页 {{ servers.length }} 项</span>
            </div>
            <div class="pa-subsection">
              <div class="pa-toolbar">
                <div class="pa-toolbar-left">
                  <select v-model="filters.is_public" class="pa-input pa-filter">
                    <option value="">全部展示状态</option>
                    <option value="true">公开展示</option>
                    <option value="false">未公开</option>
                  </select>
                  <select v-model="filters.audit_status" class="pa-input pa-filter">
                    <option value="">全部审核状态</option>
                    <option value="pending">待审核</option>
                    <option value="approved">已通过</option>
                    <option value="rejected">已驳回</option>
                  </select>
                  <select v-model="filters.status" class="pa-input pa-filter">
                    <option value="">全部平台状态</option>
                    <option value="active">运行中</option>
                    <option value="inactive">未启用</option>
                    <option value="suspended">已下架</option>
                  </select>
                  <input
                    v-model.trim="filters.q"
                    class="pa-input pa-search"
                    placeholder="搜索名称、编号、简介"
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
                    <th>服务器</th>
                    <th>审核</th>
                    <th>平台状态</th>
                    <th>展示</th>
                    <th>成员</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="server in servers"
                    :key="server.id"
                    :class="{ 'pa-table-row-active': selectedServerId === server.id }"
                  >
                    <td>
                      <strong>{{ server.name }}</strong>
                      <div class="pa-table-meta">#{{ server.id }} · {{ server.server_code || '-' }}</div>
                    </td>
                    <td>
                      <span :class="['pa-badge', auditStatusBadge(server.platform_audit_status)]">
                        {{ auditStatusLabel(server.platform_audit_status) }}
                      </span>
                    </td>
                    <td>
                      <span :class="['pa-badge', platformStatusBadge(server.platform_status)]">
                        {{ platformStatusLabel(server.platform_status) }}
                      </span>
                    </td>
                    <td>
                      <span :class="['pa-badge', server.platform_is_public ? 'pa-badge-green' : 'pa-badge-gray']">
                        {{ server.platform_is_public ? '公开' : '未公开' }}
                      </span>
                    </td>
                    <td>{{ server.members_count || 0 }}</td>
                    <td>
                      <div class="pa-split-actions">
                        <button class="pa-btn pa-btn-sm pa-btn-outline" @click="showServerDetail(server.id)">详情</button>
                        <button
                          v-if="canApprove(server)"
                          class="pa-btn pa-btn-sm pa-btn-primary"
                          @click="approve(server)"
                        >
                          通过
                        </button>
                        <button
                          v-if="canReject(server)"
                          class="pa-btn pa-btn-sm pa-btn-outline"
                          @click="prepareAction('reject', server)"
                        >
                          驳回
                        </button>
                        <button
                          v-if="canSuspend(server)"
                          class="pa-btn pa-btn-sm pa-btn-outline"
                          @click="requestSuspend(server)"
                        >
                          下架
                        </button>
                        <button
                          v-if="canRestore(server)"
                          class="pa-btn pa-btn-sm pa-btn-outline"
                          @click="requestRestore(server)"
                        >
                          恢复
                        </button>
                        <template v-if="confirmSuspendId === server.id">
                          <button class="pa-btn pa-btn-sm pa-btn-danger" @click="confirmSuspend(server)">确认下架</button>
                          <button class="pa-btn pa-btn-sm pa-btn-outline" @click="cancelSuspend">取消</button>
                        </template>
                        <template v-if="confirmRestoreId === server.id">
                          <button class="pa-btn pa-btn-sm pa-btn-primary" @click="confirmRestore(server)">确认恢复</button>
                          <button class="pa-btn pa-btn-sm pa-btn-outline" @click="cancelRestore">取消</button>
                        </template>
                      </div>
                    </td>
                  </tr>
                  <tr v-if="!servers.length">
                    <td colspan="6" class="pa-empty-row">暂无服务器</td>
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

    <div v-if="serverDetail" class="pa-modal-overlay pa-detail-overlay" @click.self="closeServerDetail">
      <div class="pa-modal pa-detail-modal">
        <div class="pa-modal-head">
          <div class="pa-modal-title-block">
            <h3>服务器详情与处置</h3>
            <span class="pa-section-meta">#{{ serverDetail.id }} · {{ serverDetail.server_code || '-' }}</span>
          </div>
          <button class="pa-modal-close" @click="closeServerDetail">x</button>
        </div>
        <div class="pa-modal-body">
          <div class="pa-drawer-profile pa-server-profile" :class="serverProfileClass(serverDetail)">
            <div class="pa-server-avatar">{{ serverInitial(serverDetail.name) }}</div>
            <div class="pa-account-main">
              <div class="pa-account-title-row">
                <strong>{{ serverDetail.name }}</strong>
                <span :class="['pa-badge', auditStatusBadge(serverDetail.platform_audit_status)]">
                  {{ auditStatusLabel(serverDetail.platform_audit_status) }}
                </span>
              </div>
              <div class="pa-meta">
                服主 {{ ownerAccounts(serverDetail).length }} 个 · 成员 {{ memberAccounts(serverDetail).length }} 个
              </div>
            </div>
          </div>

          <div class="pa-account-metrics">
            <div class="pa-metric-tile">
              <span>平台状态</span>
              <strong>{{ platformStatusLabel(serverDetail.platform_status) }}</strong>
            </div>
            <div class="pa-metric-tile">
              <span>展示状态</span>
              <strong>{{ serverDetail.platform_is_public ? '公开' : '未公开' }}</strong>
            </div>
            <div class="pa-metric-tile">
              <span>成员数</span>
              <strong>{{ serverDetail.members_count || 0 }}</strong>
            </div>
          </div>

          <div class="pa-drawer-sections">
            <section class="pa-modal-card">
              <div class="pa-account-list-head">
                <span class="pa-subsection-label">关联账号</span>
                <span class="pa-meta">{{ serverDetail.members?.length || 0 }} 项</span>
              </div>
              <div class="pa-server-account-groups">
                <div>
                  <div class="pa-mini-title">服主账号</div>
                  <div class="pa-list pa-modal-scroll-list is-short">
                    <article v-for="member in ownerAccounts(serverDetail)" :key="`owner-${member.user_id}`" class="pa-list-card pa-server-mini-card">
                      <div class="pa-list-main">
                        <div class="pa-card-head">
                          <strong>{{ member.email }}</strong>
                          <span class="pa-badge pa-badge-blue">服主</span>
                        </div>
                        <div class="pa-meta">用户 ID：{{ member.user_id }} · 加入于 {{ fmtTime(member.joined_at) }}</div>
                      </div>
                    </article>
                    <div v-if="!ownerAccounts(serverDetail).length" class="pa-empty">暂无服主账号</div>
                  </div>
                </div>
                <div>
                  <div class="pa-mini-title">其他成员账号</div>
                  <div class="pa-list pa-modal-scroll-list">
                    <article v-for="member in memberAccounts(serverDetail)" :key="`member-${member.user_id}`" class="pa-list-card pa-server-mini-card">
                      <div class="pa-list-main">
                        <div class="pa-card-head">
                          <strong>{{ member.email }}</strong>
                          <span class="pa-badge pa-badge-gray">{{ roleLabel(member.role) }}</span>
                        </div>
                        <div class="pa-meta">用户 ID：{{ member.user_id }} · 加入于 {{ fmtTime(member.joined_at) }}</div>
                      </div>
                    </article>
                    <div v-if="!memberAccounts(serverDetail).length" class="pa-empty">暂无其他成员账号</div>
                  </div>
                </div>
              </div>
            </section>

            <section class="pa-modal-card">
              <div class="pa-account-list-head">
                <span class="pa-subsection-label">基础信息</span>
                <span class="pa-meta">公开信息</span>
              </div>
              <div class="pa-server-info-grid is-compact">
                <div>
                  <span>游戏地址</span>
                  <strong>{{ serverDetail.game_ip || '-' }}:{{ serverDetail.game_port || '-' }}</strong>
                </div>
                <div>
                  <span>游戏版本</span>
                  <strong>{{ serverDetail.game_version || '-' }}</strong>
                </div>
                <div>
                  <span>QQ群</span>
                  <strong>{{ serverDetail.qq_group || '-' }}</strong>
                </div>
                <div>
                  <span>入服审核</span>
                  <strong>{{ serverDetail.join_requires_approval ? '需要审核' : '自动通过' }}</strong>
                </div>
              </div>
              <div class="pa-server-description">
                {{ serverDetail.description || '暂无简介' }}
              </div>
              <div v-if="serverDetail.platform_audit_reason" class="pa-action-context">
                <strong>审核备注</strong>
                <span>{{ serverDetail.platform_audit_reason }}</span>
              </div>
            </section>

            <section class="pa-modal-card">
              <div class="pa-account-list-head">
                <span class="pa-subsection-label">审核与展示</span>
                <span class="pa-meta">{{ detailActionCount(serverDetail) }} 项</span>
              </div>
              <div class="pa-split-actions">
                <button
                  v-if="canApprove(serverDetail)"
                  class="pa-btn pa-btn-sm pa-btn-primary"
                  @click="approve(serverDetail)"
                >
                  审核通过
                </button>
                <button
                  v-if="canReject(serverDetail)"
                  class="pa-btn pa-btn-sm pa-btn-outline"
                  @click="prepareAction('reject', serverDetail)"
                >
                  驳回审核
                </button>
                <button
                  v-if="canPublish(serverDetail)"
                  class="pa-btn pa-btn-sm pa-btn-outline"
                  @click="publish(serverDetail.id)"
                >
                  公开展示
                </button>
                <button
                  v-if="canUnpublish(serverDetail)"
                  class="pa-btn pa-btn-sm pa-btn-outline"
                  @click="unpublish(serverDetail.id)"
                >
                  取消公开
                </button>
                <span v-if="!detailActionCount(serverDetail)" class="pa-meta">无可用操作</span>
              </div>
              <div v-if="actionDraft.server_id && actionDraft.kind === 'reject'" class="pa-form-grid pa-action-draft">
                <div class="pa-action-context">
                  <strong>{{ actionLabel(actionDraft.kind) }}</strong>
                  <span>目标服务器：{{ actionDraft.server_name }}</span>
                </div>
                <textarea
                  v-model.trim="actionDraft.reason"
                  :class="['pa-input', { 'pa-input-error': actionError && !actionDraft.reason }]"
                  rows="4"
                  :placeholder="actionPlaceholder(actionDraft.kind)"
                  @input="actionError = ''"
                ></textarea>
                <div v-if="actionError" class="pa-form-error">{{ actionError }}</div>
                <div class="pa-split-actions">
                  <button class="pa-btn pa-btn-primary" @click="submitDraftAction">确认驳回</button>
                  <button class="pa-btn pa-btn-outline" @click="resetDraftAction">取消</button>
                </div>
              </div>
            </section>

            <section class="pa-modal-card">
              <div class="pa-account-list-head">
                <span class="pa-subsection-label">定向公告</span>
                <span class="pa-meta">服务器公告</span>
              </div>
              <div class="pa-split-actions">
                <button class="pa-btn pa-btn-primary" @click="openServerAnnouncementModal">发送服务器公告</button>
              </div>
            </section>

            <section class="pa-modal-card pa-modal-card-danger">
              <div class="pa-account-list-head">
                <span class="pa-subsection-label">下架与删除</span>
              </div>
              <div v-if="actionDraft.server_id && actionDraft.kind !== 'reject'" class="pa-form-grid">
                <div class="pa-action-context">
                  <strong>{{ actionLabel(actionDraft.kind) }}</strong>
                  <span>目标服务器：{{ actionDraft.server_name }}</span>
                </div>
                <textarea
                  v-model.trim="actionDraft.reason"
                  :class="['pa-input', { 'pa-input-error': actionError && !actionDraft.reason }]"
                  rows="4"
                  :placeholder="actionPlaceholder(actionDraft.kind)"
                  @input="actionError = ''"
                ></textarea>
                <div v-if="actionError" class="pa-form-error">{{ actionError }}</div>
                <div class="pa-split-actions">
                  <button class="pa-btn pa-btn-primary" @click="submitDraftAction">确认执行</button>
                  <button class="pa-btn pa-btn-outline" @click="resetDraftAction">取消</button>
                </div>
              </div>
              <div v-else class="pa-split-actions">
                <button class="pa-btn pa-btn-sm pa-btn-outline" @click="prepareAction('soft-delete', serverDetail)">下架</button>
                <button class="pa-btn pa-btn-sm pa-btn-danger" @click="prepareAction('hard-delete', serverDetail)">删除</button>
              </div>
            </section>
          </div>
        </div>
        <div class="pa-modal-foot">
          <button class="pa-btn pa-btn-outline" @click="closeServerDetail">关闭</button>
        </div>
      </div>
    </div>
    <!-- 服务器公告模态框 -->
    <div v-if="showAnnounceModal" class="pa-modal-overlay" @click.self="closeServerAnnouncementModal">
      <div class="pa-modal">
        <div class="pa-modal-head">
          <h3>发送服务器公告</h3>
          <button class="pa-toast-close" @click="closeServerAnnouncementModal">x</button>
        </div>
        <div class="pa-modal-body">
          <div class="pa-form-grid">
            <div class="pa-action-context">
              <strong>目标服务器：{{ serverDetail?.name }} (ID: {{ serverDetail?.id }})</strong>
              <span>仅该服务器拥有「接收服务器公告」权限的用户可见</span>
            </div>
            <input
              v-model.trim="serverAnnounceForm.title"
              :class="['pa-input', { 'pa-input-error': serverAnnounceError && !serverAnnounceForm.title }]"
              placeholder="公告标题"
              @input="serverAnnounceError = ''"
            />
            <textarea
              v-model.trim="serverAnnounceForm.content"
              :class="['pa-input', { 'pa-input-error': serverAnnounceError && !serverAnnounceForm.content }]"
              rows="4"
              placeholder="公告内容"
              @input="serverAnnounceError = ''"
            ></textarea>
            <div v-if="serverAnnounceError" class="pa-form-error">{{ serverAnnounceError }}</div>
            <div class="pa-inline-form">
              <label class="pa-checkline"><input v-model="serverAnnounceForm.is_important" type="checkbox" />标记为重要公告</label>
            </div>
          </div>
        </div>
        <div class="pa-modal-foot">
          <button class="pa-btn pa-btn-outline" @click="closeServerAnnouncementModal">取消</button>
          <button class="pa-btn pa-btn-primary" :disabled="submittingAnnounce" @click="sendServerAnnouncement">
            {{ submittingAnnounce ? '发送中…' : '发送公告' }}
          </button>
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
  auditPlatformServer,
  createAnnouncement,
  deletePlatformServer,
  getPlatformServerDetail,
  hardDeletePlatformServer,
  listPlatformServers,
  publishPlatformServer,
  unpublishPlatformServer,
  updatePlatformServerStatus,
} from '@/api/platform'
import './platform-admin.css'

const loading = ref(false)
const servers = ref([])
const serverDetail = ref(null)
const selectedServerId = ref(null)
const confirmSuspendId = ref(null)
const confirmRestoreId = ref(null)
const toast = reactive({ message: '', type: 'ok' })
const filters = reactive({ q: '', status: '', audit_status: '', is_public: '' })
const pagination = reactive({ page: 1, limit: 20, total: 0 })
const serverAnnounceForm = reactive({ title: '', content: '', is_important: false })
const serverAnnounceError = ref('')
const showAnnounceModal = ref(false)
const submittingAnnounce = ref(false)
const actionDraft = reactive({ kind: '', server_id: null, server_name: '', reason: '' })
const actionError = ref('')
const totalPages = computed(() => Math.max(1, Math.ceil((pagination.total || 0) / pagination.limit)))

function showToast(message, type = 'ok') {
  toast.message = message
  toast.type = type
}

function clearToast() {
  toast.message = ''
}

function s(v) { return v == null ? '' : (typeof v === 'string' ? v : String(v)) }

function auditStatusLabel(status) {
  return ({ pending: '待审核', approved: '已通过', rejected: '已驳回' })[s(status)] || s(status) || '-'
}

function platformStatusLabel(status) {
  return ({ active: '运行中', inactive: '未启用', suspended: '已下架' })[s(status)] || s(status) || '-'
}

function roleLabel(role) {
  const r = typeof role === 'object' && role ? (role.value || role.name || String(role)) : role
  return ({ owner: '服主', web_staff: '管理成员', member: '普通成员' })[r] || s(r) || '-'
}

function fmtTime(ts) {
  if (!ts || typeof ts !== 'number') return '-'
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

function auditStatusBadge(status) {
  return ({ pending: 'pa-badge-orange', approved: 'pa-badge-green', rejected: 'pa-badge-red' })[status] || 'pa-badge-gray'
}

function platformStatusBadge(status) {
  return ({ active: 'pa-badge-green', inactive: 'pa-badge-gray', suspended: 'pa-badge-red' })[status] || 'pa-badge-gray'
}

function serverInitial(name) {
  return String(name || '?').trim().slice(0, 1).toUpperCase()
}

function serverProfileClass(server) {
  if (!server) return ''
  if (server.platform_status === 'suspended') return 'is-suspended'
  if (server.platform_audit_status === 'rejected') return 'is-rejected'
  if (server.platform_audit_status === 'pending') return 'is-pending'
  return ''
}

function ownerAccounts(server) {
  return server?.owner_accounts || server?.members?.filter((member) => member.is_owner) || []
}

function memberAccounts(server) {
  return server?.members?.filter((member) => !member.is_owner) || []
}

function canApprove(server) {
  return server && server.platform_audit_status !== 'approved'
}

function canReject(server) {
  return server && server.platform_audit_status === 'pending'
}

function canSuspend(server) {
  return server && server.platform_status === 'active'
}

function canRestore(server) {
  return server && server.platform_status !== 'active' && server.platform_audit_status === 'approved'
}

function canPublish(server) {
  return server && server.platform_audit_status === 'approved' && server.platform_status === 'active' && !server.platform_is_public
}

function canUnpublish(server) {
  return server && server.platform_is_public
}

function availableDisplayActions(server) {
  return [
    canApprove(server),
    canPublish(server),
    canUnpublish(server),
    canRestore(server),
    canSuspend(server),
  ].filter(Boolean)
}

function availableDetailActions(server) {
  return [
    canApprove(server),
    canPublish(server),
    canUnpublish(server),
  ].filter(Boolean)
}

function detailActionCount(server) {
  return availableDetailActions(server).length + (canReject(server) ? 1 : 0)
}

function actionLabel(kind) {
  return ({
    reject: '驳回审核',
    'soft-delete': '下架服务器',
    'hard-delete': '删除服务器',
  })[kind] || '平台处置'
}

function actionPlaceholder(kind) {
  return ({
    reject: '填写驳回原因，平台会记录并反馈给服务器方',
    'soft-delete': '填写下架原因',
    'hard-delete': '填写删除原因',
  })[kind] || '填写操作原因'
}

function normalizedFilters() {
  return {
    q: filters.q,
    status: filters.status,
    audit_status: filters.audit_status,
    is_public: filters.is_public === '' ? '' : filters.is_public === 'true',
    skip: (pagination.page - 1) * pagination.limit,
    limit: pagination.limit,
  }
}

async function loadServers() {
  loading.value = true
  clearToast()
  try {
    const data = await listPlatformServers(normalizedFilters())
    const items = Array.isArray(data) ? data : (data.items || [])
    servers.value = items
    pagination.total = Array.isArray(data) ? items.length : (data.total || 0)
    if (pagination.page > totalPages.value) {
      pagination.page = totalPages.value
      await loadServers()
    }
  } catch (e) {
    showToast(e.message || '加载服务器失败', 'err')
  } finally {
    loading.value = false
  }
}

async function loadAll() {
  await loadServers()
  if (selectedServerId.value) await showServerDetail(selectedServerId.value)
}

function applyFilters() {
  pagination.page = 1
  loadServers()
}

function goPage(page) {
  pagination.page = Math.min(Math.max(1, page), totalPages.value)
  loadServers()
}

function resetFilters() {
  filters.q = ''
  filters.status = ''
  filters.audit_status = ''
  filters.is_public = ''
  pagination.page = 1
  loadServers()
}

async function showServerDetail(id, resetAction = true) {
  try {
    selectedServerId.value = id
    serverDetail.value = await getPlatformServerDetail(id)
    if (resetAction) resetDraftAction()
  } catch (e) {
    showToast(e.message || '加载服务器详情失败', 'err')
  }
}

function closeServerDetail() {
  serverDetail.value = null
  selectedServerId.value = null
  resetDraftAction()
}

async function approve(server) {
  const id = server?.id
  if (!id) return
  const detailOpen = serverDetail.value?.id === id
  try {
    await auditPlatformServer(id, 'approve', '')
    showToast('服务器已审核通过')
    await loadServers()
    if (detailOpen) await showServerDetail(id)
  } catch (e) {
    showToast(e.message || '审核失败', 'err')
  }
}

async function publish(id) {
  const detailOpen = serverDetail.value?.id === id
  try {
    await publishPlatformServer(id)
    showToast('服务器已公开展示')
    await loadServers()
    if (detailOpen) await showServerDetail(id)
  } catch (e) {
    showToast(e.message || '公开展示失败', 'err')
  }
}

async function unpublish(id) {
  const detailOpen = serverDetail.value?.id === id
  try {
    await unpublishPlatformServer(id)
    showToast('服务器已取消公开')
    await loadServers()
    if (detailOpen) await showServerDetail(id)
  } catch (e) {
    showToast(e.message || '取消公开失败', 'err')
  }
}

async function setActive(id) {
  const detailOpen = serverDetail.value?.id === id
  try {
    await updatePlatformServerStatus(id, 'active', '平台手动恢复')
    showToast('服务器已恢复运行')
    await loadServers()
    if (detailOpen) await showServerDetail(id)
  } catch (e) {
    showToast(e.message || '恢复运行失败', 'err')
  }
}

function requestSuspend(server) {
  if (!server?.id) return
  confirmSuspendId.value = confirmSuspendId.value === server.id ? null : server.id
  confirmRestoreId.value = null
  selectedServerId.value = server.id
}

function cancelSuspend() {
  confirmSuspendId.value = null
}

function requestRestore(server) {
  if (!server?.id) return
  confirmRestoreId.value = confirmRestoreId.value === server.id ? null : server.id
  confirmSuspendId.value = null
  selectedServerId.value = server.id
}

function cancelRestore() {
  confirmRestoreId.value = null
}

async function confirmSuspend(server) {
  const id = server?.id
  if (!id) return
  try {
    await updatePlatformServerStatus(id, 'suspended', '平台手动下架')
    confirmSuspendId.value = null
    showToast('服务器已下架')
    await loadServers()
    if (serverDetail.value?.id === id) await showServerDetail(id)
  } catch (e) {
    showToast(e.message || '下架失败', 'err')
  }
}

async function confirmRestore(server) {
  const id = server?.id
  if (!id) return
  try {
    await updatePlatformServerStatus(id, 'active', '平台手动恢复')
    confirmRestoreId.value = null
    showToast('服务器已恢复运行')
    await loadServers()
    if (serverDetail.value?.id === id) await showServerDetail(id)
  } catch (e) {
    showToast(e.message || '恢复运行失败', 'err')
  }
}

function prepareAction(kind, server) {
  selectedServerId.value = server.id
  actionDraft.kind = kind
  actionDraft.server_id = server.id
  actionDraft.server_name = server.name
  actionDraft.reason = ''
  actionError.value = ''
  if (!serverDetail.value || serverDetail.value.id !== server.id) showServerDetail(server.id, false)
}

function resetDraftAction() {
  actionDraft.kind = ''
  actionDraft.server_id = null
  actionDraft.server_name = ''
  actionDraft.reason = ''
  actionError.value = ''
}

async function submitDraftAction() {
  if (!actionDraft.server_id || !actionDraft.kind) return
  if (!actionDraft.reason) {
    actionError.value = actionDraft.kind === 'reject' ? '请填写驳回原因' : '请填写操作原因'
    return
  }
  const currentId = actionDraft.server_id
  const currentKind = actionDraft.kind
  try {
    if (currentKind === 'reject') {
      await auditPlatformServer(currentId, 'reject', actionDraft.reason)
    } else if (currentKind === 'soft-delete') {
      await deletePlatformServer(currentId, actionDraft.reason)
    } else if (currentKind === 'hard-delete') {
      await hardDeletePlatformServer(currentId, actionDraft.reason)
      serverDetail.value = null
      selectedServerId.value = null
    }
    showToast(`${actionLabel(currentKind)}已执行`)
    resetDraftAction()
    await loadServers()
    if (serverDetail.value?.id === currentId) await showServerDetail(currentId)
  } catch (e) {
    showToast(e.message || '执行平台操作失败', 'err')
  }
}

function openServerAnnouncementModal() {
  Object.assign(serverAnnounceForm, { title: '', content: '', is_important: false })
  serverAnnounceError.value = ''
  showAnnounceModal.value = true
}

function closeServerAnnouncementModal() {
  serverAnnounceError.value = ''
  showAnnounceModal.value = false
}

async function sendServerAnnouncement() {
  const id = serverDetail.value?.id
  if (!serverAnnounceForm.title || !serverAnnounceForm.content) {
    serverAnnounceError.value = '必填项不能为空'
    return
  }
  if (!id) return
  submittingAnnounce.value = true
  try {
    const result = await createAnnouncement({
      target_type: 'server',
      server_id: id,
      title: serverAnnounceForm.title,
      content: serverAnnounceForm.content,
      is_important: serverAnnounceForm.is_important,
    })
    closeServerAnnouncementModal()
    Object.assign(serverAnnounceForm, { title: '', content: '', is_important: false })
    const count = Number(result?.notification?.receiver_count || 0)
    showToast(count > 0 ? `服务器公告已发送，已通知 ${count} 个拥有面板权限的成员` : '服务器公告已保存，暂无可通知成员')
  } catch (e) {
    showToast(e.message || '发送公告失败', 'err')
  } finally {
    submittingAnnounce.value = false
  }
}

onMounted(loadAll)
</script>
