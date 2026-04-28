<template>
  <div class="messages-page">
    <!-- ── 顶部标题栏 ── -->
    <PageHeader title="消息中心" subtitle="查看邀请、审批结果与系统通知" heading-tag="h1">
      <template #meta>
        <span v-if="unreadCount > 0" class="unread-chip">{{ unreadCount }} 条未读</span>
      </template>
      <template #actions>
        <button class="btn btn-outline" @click="reloadAll" :disabled="loading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
          </svg>
          刷新
        </button>
      </template>
    </PageHeader>

    <div class="page-body">
      <div class="tab-bar">
        <button :class="['tab-btn', tab === 'notifications' && 'active']" @click="tab = 'notifications'">
          通知
          <span class="tab-count">{{ visibleMessages.length }}</span>
        </button>
        <button :class="['tab-btn', tab === 'invites' && 'active']" @click="tab = 'invites'">
          邀请
          <span class="tab-count">{{ invites.length }}</span>
        </button>
        <button :class="['tab-btn', tab === 'requests' && 'active']" @click="tab = 'requests'">
          申请
          <span class="tab-count">{{ myRequests.length }}</span>
        </button>
      </div>

      <div v-if="success" class="success-box">{{ success }}</div>
      <div v-if="error" class="error-box">{{ error }}</div>

    <div v-if="tab === 'notifications'" class="panel">
      <div class="panel-actions">
        <div class="message-filter-row">
          <input
            v-model.trim="messageSearch"
            class="message-search"
            placeholder="搜索标题、内容、来源或编号"
            @keyup.enter="loadMessages"
          />
          <select v-model="messageCategory" class="message-category" @change="loadMessages">
            <option value="all">全部通知</option>
            <option value="join">入服申请</option>
            <option value="invite">服务器邀请</option>
            <option value="announcement">公告</option>
            <option value="system">系统通知</option>
          </select>
          <label class="check-line">
            <input type="checkbox" v-model="onlyUnread" @change="loadMessages" />
            只看未读
          </label>
          <button class="btn btn-sm btn-outline" @click="loadMessages" :disabled="loading">搜索</button>
          <button v-if="messageSearch || messageCategory !== 'all' || onlyUnread" class="btn btn-sm btn-outline" @click="resetMessageFilters">重置</button>
        </div>
        <button class="btn btn-sm btn-outline" @click="readAll" :disabled="loading">全部标记已读</button>
      </div>

      <div v-if="loading" class="state-tip">加载中...</div>
      <div v-else-if="!visibleMessages.length" class="state-tip">暂无消息</div>
      <div v-else class="list-wrap">
        <article v-for="m in visibleMessages" :key="m.id" class="message-card" :class="{ unread: !m.read_at }">
          <div class="message-head">
            <span :class="['msg-type-badge', `msg-type-${m.type}`]">{{ msgTypeLabel(m.type) }}</span>
            <span class="message-time">{{ fmtTime(m.created_at) }}</span>
          </div>
          <div class="message-body">
            <div class="message-title">{{ m.title }}</div>
            <div>
              <span class="msg-source">{{ formatMsgSource(m) }}</span>
              {{ m.content }}
            </div>
          </div>
          <details v-if="messageBlacklistDetails(m).length" class="message-blacklist-box">
            <summary>黑名单明细：{{ messageBlacklistSummary(m) }}</summary>
            <div class="message-blacklist-list">
              <div v-for="item in messageBlacklistDetails(m)" :key="`${m.id}-${item.scope}-${item.id}`" class="message-blacklist-item">
                <div class="message-blacklist-head">
                  <span>{{ item.label }}</span>
                  <span>{{ fmtTime(item.reviewed_at || item.created_at) }}</span>
                </div>
                <div class="message-blacklist-reason">{{ item.reason || '未填写原因' }}</div>
                <div class="message-blacklist-meta">
                  <span v-if="item.source_server_name">来源：{{ item.source_server_name }}</span>
                  <span v-if="item.operator_email">提交人：{{ item.operator_email }}</span>
                  <span v-if="item.review_note">审核备注：{{ item.review_note }}</span>
                </div>
              </div>
            </div>
          </details>
          <div class="message-foot" v-if="!m.read_at">
            <button class="btn btn-sm btn-primary" @click="readOne(m.id)">标记已读</button>
          </div>
        </article>
      </div>
    </div>

    <div v-else-if="tab === 'invites'" class="panel">
      <div class="panel-actions">
        <span class="panel-label">待处理邀请</span>
      </div>

      <div v-if="loading" class="state-tip">加载中...</div>
      <div v-else-if="!invites.length" class="state-tip">暂无待处理邀请</div>
      <div v-else class="list-wrap">
        <article v-for="inv in invites" :key="inv.id" class="invite-card">
          <div class="message-head">
            <span class="msg-type-badge msg-type-invite">服务器邀请</span>
            <span class="message-time">{{ fmtTime(inv.created_at) }}</span>
          </div>
          <div class="message-body">
            <span class="msg-source">{{ displayServerName(inv.server_name) }}</span>
            <span class="message-seq">序号：{{ displayServerCode(inv.server_code) }}</span>
            {{ inv.inviter_email || '未知用户' }} 邀请你加入
          </div>
          <div class="card-meta-row">
            <span v-if="inv.message" class="card-meta">附言：{{ inv.message }}</span>
            <span v-if="inv.expires_at" class="card-meta">过期：{{ fmtTime(inv.expires_at) }}</span>
          </div>
          <div class="invite-actions">
            <button class="btn btn-sm btn-primary" @click="handleInvite(inv.id, 'accept')">接受</button>
            <button class="btn btn-sm btn-outline" @click="handleInvite(inv.id, 'reject')">拒绝</button>
          </div>
        </article>
      </div>
    </div>

    <div v-else class="panel request-panel">
      <section class="section-block">
        <div class="panel-actions">
          <h3 class="section-title">我的申请记录</h3>
        </div>
        <p class="section-tip">发起新申请请前往「服务器」-「我加入的」中的"申请未公开服务器"。</p>
        <div v-if="!myRequests.length" class="state-tip">暂无申请记录</div>
        <div v-else class="list-wrap">
          <article v-for="req in myRequests" :key="req.id" class="request-card">
            <div class="message-head">
              <span class="msg-type-badge msg-type-request">入服申请</span>
              <span :class="['status-chip', `status-${req.status}`]">{{ statusLabel(req.status) }}</span>
            </div>
            <div class="message-body">
              <span class="msg-source">{{ displayServerName(req.server_name) }}</span>
              <span class="message-seq">序号：{{ displayServerCode(req.server_code) }}</span>
              申请加入服务器
            </div>
            <div class="card-meta-row">
              <span class="card-meta">{{ fmtTime(req.created_at) }}</span>
              <span v-if="req.message" class="card-meta">附言：{{ req.message }}</span>
              <span v-if="req.review_note" class="card-meta">审批备注：{{ req.review_note }}</span>
            </div>
            <div class="invite-actions" v-if="req.status === 'pending'">
              <button class="btn btn-sm btn-outline" @click="withdrawRequest(req.id)">撤回申请</button>
            </div>
          </article>
        </div>
      </section>
    </div>
    </div><!-- /.page-body -->
  </div>
</template>

<script setup>
import { computed, inject, onMounted, ref } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import {
  listMyJoinRequests,
  listMessages,
  getUnreadCount,
  markMessageRead,
  markAllMessagesRead,
  listMyInvites,
  respondInvite,
  withdrawMyJoinRequest,
} from '@/api/messages'

const tab = ref('notifications')
const loading = ref(false)
const error = ref('')
const success = ref('')
const onlyUnread = ref(false)
const messageSearch = ref('')
const messageCategory = ref('all')

const unreadCount = ref(0)
const messages = ref([])
const invites = ref([])
const myRequests = ref([])
const reloadServers = inject('reloadServers', null)

const visibleMessages = computed(() => messages.value)

// 消息类型 → 中文标签映射
const MSG_TYPE_LABELS = {
  join_request_pending: '入服申请',
  join_request_result: '入服结果',
  join_request_approved: '申请已通过',
  join_request_rejected: '申请已拒绝',
  join_request_withdrawn: '申请已撤回',
  invite: '收到邀请',
  invite_sent: '收到邀请',
  invite_accepted: '邀请已接受',
  invite_rejected: '邀请已拒绝',
  invite_expired: '邀请已过期',
  system: '系统通知',
  announcement: '公告',
}

function msgTypeLabel(type) {
  const t = type == null ? '' : (typeof type === 'string' ? type : String(type))
  return MSG_TYPE_LABELS[t] || t || '系统通知'
}

// 申请状态 → 中文标签
const STATUS_LABELS = {
  pending: '待审批',
  approved: '已通过',
  rejected: '已拒绝',
  withdrawn: '已撤回',
}

function statusLabel(status) {
  return STATUS_LABELS[status] || status
}

// 格式化消息来源：有服务器名则显示服务器名，否则显示平台通知
function formatMsgSource(m) {
  if (m.server_name) {
    return m.server_name
  }
  return '平台通知'
}

function displayServerName(name) {
  const value = String(name || '').trim()
  return value || '未命名服务器'
}

function displayServerCode(code) {
  const value = String(code || '').trim()
  return value || '-'
}

function messagePayload(m) {
  if (!m?.payload_json) return {}
  try {
    const parsed = JSON.parse(m.payload_json)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

function messageBlacklistDetails(m) {
  const details = messagePayload(m)?.blacklist?.blacklist_details
  return Array.isArray(details) ? details : []
}

function messageBlacklistSummary(m) {
  const blacklist = messagePayload(m)?.blacklist || {}
  const local = Number(blacklist.server_blacklist_count || 0)
  const cloud = Number(blacklist.cloud_blacklist_count || 0)
  const parts = []
  if (local) parts.push(`本服务器黑名单 ${local} 条`)
  if (cloud) parts.push(`平台云黑 ${cloud} 条`)
  return parts.join(' / ') || `${messageBlacklistDetails(m).length} 条`
}

function showSuccess(text) {
  success.value = text
  setTimeout(() => {
    success.value = ''
  }, 2000)
}

function fmtTime(ts) {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleString()
}

async function loadUnreadCount() {
  const data = await getUnreadCount()
  unreadCount.value = Number(data?.unread || 0)
}

async function loadMessages() {
  loading.value = true
  error.value = ''
  try {
    messages.value = await listMessages({
      unreadOnly: onlyUnread.value,
      q: messageSearch.value,
      category: messageCategory.value,
      limit: 100,
      offset: 0,
    })
    await loadUnreadCount()
  } catch (e) {
    error.value = e.message || '加载消息失败'
  } finally {
    loading.value = false
  }
}

function resetMessageFilters() {
  messageSearch.value = ''
  messageCategory.value = 'all'
  onlyUnread.value = false
  loadMessages()
}

async function loadInvites() {
  loading.value = true
  error.value = ''
  try {
    invites.value = await listMyInvites('pending')
  } catch (e) {
    error.value = e.message || '加载邀请失败'
  } finally {
    loading.value = false
  }
}

async function loadMyRequests() {
  loading.value = true
  error.value = ''
  try {
    myRequests.value = await listMyJoinRequests('')
  } catch (e) {
    error.value = e.message || '加载申请失败'
  } finally {
    loading.value = false
  }
}

async function readOne(id) {
  try {
    await markMessageRead(id)
    await loadMessages()
  } catch (e) {
    error.value = e.message || '操作失败'
  }
}

async function readAll() {
  try {
    await markAllMessagesRead()
    await loadMessages()
  } catch (e) {
    error.value = e.message || '操作失败'
  }
}

async function handleInvite(inviteId, action) {
  try {
    await respondInvite(inviteId, action)
    if (action === 'accept' && typeof reloadServers === 'function') {
      await reloadServers()
    }
    showSuccess(action === 'accept' ? '已接受邀请' : '已拒绝邀请')
    await Promise.all([loadInvites(), loadMessages()])
  } catch (e) {
    error.value = e.message || '处理邀请失败'
  }
}

async function withdrawRequest(requestId) {
  try {
    await withdrawMyJoinRequest(requestId)
    showSuccess('申请已撤回')
    await loadMyRequests()
  } catch (e) {
    error.value = e.message || '撤回失败'
  }
}

async function reloadAll() {
  await Promise.all([
    loadMessages(),
    loadInvites(),
    loadMyRequests(),
  ])
}

onMounted(async () => {
  await Promise.all([loadMessages(), loadInvites(), loadMyRequests()])
})
</script>

<style scoped>
/* ── 页面容器 ── */
.messages-page {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  background: #f8fafc;
}

.unread-chip {
  font-size: 12px;
  color: #d97706;
  background: #fef3c7;
  border: 1px solid #fde68a;
  padding: 2px 8px;
  border-radius: 20px;
}

/* ── 页面主体 ── */
.page-body {
  flex: 1;
  padding: 20px 28px 24px;
}

/* ── Tab 标签栏（与 cfg-cats 一致） ── */
.tab-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 14px;
  border-radius: 20px;
  font-size: 12px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #374151;
  cursor: pointer;
  transition: all 0.15s;
  font-weight: 500;
}

.tab-btn:hover {
  background: #f8fafc;
  border-color: #94a3b8;
}

.tab-btn.active {
  background: #3b82f6;
  color: #fff;
  border-color: #3b82f6;
}

.tab-count {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 10px;
  padding: 1px 6px;
  font-size: 10px;
}

.tab-btn.active .tab-count {
  background: rgba(255, 255, 255, 0.25);
}

/* ── 面板 ── */
.panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
}

.panel-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.message-filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.message-search,
.message-category {
  box-sizing: border-box;
  padding: 7px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  color: #0f172a;
  background: #fff;
  outline: none;
  font-size: 13px;
}

.message-search {
  width: min(320px, 72vw);
}

.message-search:focus,
.message-category:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,.12);
}

.check-line {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #374151;
}

/* ── 状态提示 ── */
.state-tip {
  color: #94a3b8;
  padding: 32px 0;
  text-align: center;
  font-size: 14px;
}

/* ── 通知消息框（对齐 cfg-toast） ── */
.error-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  color: #991b1b;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 500;
}

.success-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  color: #166534;
  background: #dcfce7;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 500;
}

/* ── 列表 ── */
.list-wrap {
  display: grid;
  gap: 8px;
}

.message-card,
.invite-card,
.request-card {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px;
  background: #fff;
  transition: border-color 0.15s;
}

.message-card.unread {
  border-color: #93c5fd;
  background: #f8fbff;
}

/* ── 卡片统一结构 ── */
.message-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

/* 消息类型徽章 */
.msg-type-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid transparent;
  background: #f1f5f9;
  color: #475569;
  border-color: #e2e8f0;
}

.msg-type-join_request_approved { background: #dcfce7; color: #166534; border-color: #bbf7d0; }
.msg-type-join_request_pending,
.msg-type-join_request_result    { background: #faf5ff; color: #6d28d9; border-color: #ddd6fe; }
.msg-type-join_request_rejected  { background: #fee2e2; color: #991b1b; border-color: #fecaca; }
.msg-type-invite_accepted        { background: #dcfce7; color: #166534; border-color: #bbf7d0; }
.msg-type-invite_rejected        { background: #fee2e2; color: #991b1b; border-color: #fecaca; }
.msg-type-invite_sent,
.msg-type-invite                 { background: #eff6ff; color: #1d4ed8; border-color: #bfdbfe; }
.msg-type-request                { background: #faf5ff; color: #6d28d9; border-color: #ddd6fe; }
.msg-type-system,
.msg-type-announcement           { background: #fefce8; color: #854d0e; border-color: #fef08a; }

/* 卡片正文：服务器 + 来源：内容 */
.message-body {
  font-size: 13px;
  color: #334155;
  line-height: 1.55;
  margin-bottom: 8px;
}

.message-title {
  margin-bottom: 4px;
  color: #0f172a;
  font-weight: 700;
}

.message-blacklist-box {
  margin: 8px 0;
  padding: 8px 10px;
  border: 1px solid #fbbf24;
  border-radius: 8px;
  background: #fffbeb;
  color: #92400e;
  font-size: 12px;
  line-height: 1.45;
}

.message-blacklist-box summary {
  cursor: pointer;
  font-weight: 600;
}

.message-blacklist-list {
  display: grid;
  gap: 8px;
  margin-top: 8px;
}

.message-blacklist-item {
  padding-top: 8px;
  border-top: 1px solid #fde68a;
}

.message-blacklist-head,
.message-blacklist-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.message-blacklist-head {
  justify-content: space-between;
  color: #78350f;
  font-weight: 600;
}

.message-blacklist-reason {
  margin-top: 4px;
  color: #451a03;
  white-space: pre-wrap;
}

.message-blacklist-meta {
  margin-top: 4px;
  color: #92400e;
}

.card-server {
  font-weight: 600;
  color: #0f172a;
  margin-right: 6px;
}

.card-meta-strong {
  font-weight: 600;
  color: #475569;
  margin-right: 6px;
}

.message-seq {
  display: inline-block;
  margin-right: 6px;
  color: #475569;
  font-weight: 600;
}

/* 消息来源高亮 */
.msg-source {
  font-weight: 600;
  color: #3b82f6;
  background: #eff6ff;
  padding: 1px 6px;
  border-radius: 4px;
  margin-right: 6px;
  display: inline-block;
}

/* 卡片 meta 行 */
.card-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 2px;
}

.card-meta {
  font-size: 12px;
  color: #94a3b8;
}

.panel-label {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.message-time {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
}

.message-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-top: 8px;
}

.invite-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

/* ── 申请区 ── */
.request-panel {
  display: grid;
  gap: 14px;
}

.section-block {
  padding: 8px 0;
  background: transparent;
}

.section-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.section-tip {
  margin: 6px 0 12px;
  font-size: 12px;
  color: #64748b;
}

/* ── Status chips ── */
.status-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
  border: 1px solid transparent;
}

.status-pending {
  color: #b54708;
  background: #fffaeb;
  border-color: #fedf89;
}

.status-approved {
  color: #166534;
  background: #dcfce7;
  border-color: #bbf7d0;
}

.status-rejected,
.status-withdrawn {
  color: #991b1b;
  background: #fee2e2;
  border-color: #fecaca;
}

/* ── 按钮（与 cfg-btn 一致） ── */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  cursor: pointer;
  border-radius: 8px;
  padding: 7px 16px;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s;
}

.btn svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-sm {
  padding: 5px 12px;
  font-size: 12px;
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

/* ── 响应式 ── */
@media (max-width: 768px) {
  .page-body {
    padding: 16px;
  }
}
</style>
