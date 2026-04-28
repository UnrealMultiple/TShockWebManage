<template>
  <div class="pa-page">
    <PageHeader title="平台总览" subtitle="统计、待办与公告">
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

      <div class="pa-body pa-overview-body">
        <!-- KPI 顶栏 -->
        <div v-if="hasPerm('platform.dashboard.view')" class="pa-kpi-bar">
          <article class="pa-kpi-card">
            <span class="pa-kpi-icon" style="background:#eff6ff;color:#2563eb">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <rect x="3" y="4" width="18" height="13" rx="2"></rect>
                <path d="M8 21h8"></path>
                <path d="M12 17v4"></path>
              </svg>
            </span>
            <div class="pa-kpi-num">{{ stats.servers.total || 0 }}</div>
            <div class="pa-kpi-label">服务器总数</div>
          </article>
          <article class="pa-kpi-card">
            <span class="pa-kpi-icon" style="background:#dcfce7;color:#16a34a">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M20 6 9 17l-5-5"></path>
              </svg>
            </span>
            <div class="pa-kpi-num">{{ stats.servers.active || 0 }}</div>
            <div class="pa-kpi-label">运行中</div>
          </article>
          <article class="pa-kpi-card">
            <span class="pa-kpi-icon" style="background:#fef3c7;color:#d97706">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="12" r="8"></circle>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
            </span>
            <div class="pa-kpi-num">{{ stats.servers.public || 0 }}</div>
            <div class="pa-kpi-label">公开展示</div>
          </article>
          <article class="pa-kpi-card">
            <span class="pa-kpi-icon" style="background:#faf5ff;color:#7c3aed">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M20 21a8 8 0 0 0-16 0"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
            </span>
            <div class="pa-kpi-num">{{ stats.users.total_users || 0 }}</div>
            <div class="pa-kpi-label">平台账号</div>
          </article>
          <article class="pa-kpi-card">
            <span class="pa-kpi-icon" style="background:#fce7f3;color:#db2777">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"></path>
                <path d="m9 12 2 2 4-4"></path>
              </svg>
            </span>
            <div class="pa-kpi-num">{{ stats.users.platform_admins || 0 }}</div>
            <div class="pa-kpi-label">管理员</div>
          </article>
        </div>

        <!-- 双列主内容 -->
        <div class="pa-overview-columns">
          <!-- 左列：待处理 + 服务器状态 -->
          <div class="pa-overview-left">
            <section v-if="hasPerm('platform.dashboard.view')" class="pa-section">
              <div class="pa-section-head">
                <span class="pa-section-title">待处理事项</span>
                <span v-if="totalTodoCount" class="pa-section-badge">{{ totalTodoCount }}</span>
              </div>
              <div class="pa-todos-compact">
                <router-link to="/platform-admin/servers" class="pa-todo-chip" :class="{ 'is-hot': stats.servers.pending_audit > 0 }">
                  <span class="pa-todo-dot pa-todo-dot-orange"></span>
                  <span class="pa-todo-chip-label">服务器审核</span>
                  <strong>{{ stats.servers.pending_audit }}</strong>
                </router-link>
                <router-link to="/platform-admin/accounts" class="pa-todo-chip" :class="{ 'is-hot': stats.restrictions.total > 0 }">
                  <span class="pa-todo-dot pa-todo-dot-red"></span>
                  <span class="pa-todo-chip-label">账号限制</span>
                  <strong>{{ stats.restrictions.total || 0 }}</strong>
                </router-link>
                <div class="pa-todo-chip">
                  <span class="pa-todo-dot pa-todo-dot-yellow"></span>
                  <span class="pa-todo-chip-label">举报处理</span>
                  <strong>{{ pendingReportCount }}</strong>
                  <span class="pa-todo-chip-sub">待{{ stats.reports.pending || 0 }} / 处理中{{ stats.reports.processing || 0 }}</span>
                </div>
              </div>

              <div class="pa-server-breakdown">
                <div class="pa-breakdown-title">服务器状态分布</div>
                <div class="pa-breakdown-bars">
                  <div class="pa-breakdown-row">
                    <span class="pa-breakdown-label">运行中</span>
                    <div class="pa-breakdown-track">
                      <div class="pa-breakdown-fill" :style="{ width: percent(stats.servers.active, stats.servers.total), background: '#22c55e' }"></div>
                    </div>
                    <strong>{{ stats.servers.active || 0 }}</strong>
                  </div>
                  <div class="pa-breakdown-row">
                    <span class="pa-breakdown-label">未启用</span>
                    <div class="pa-breakdown-track">
                      <div class="pa-breakdown-fill" :style="{ width: percent(stats.servers.inactive, stats.servers.total), background: '#94a3b8' }"></div>
                    </div>
                    <strong>{{ stats.servers.inactive || 0 }}</strong>
                  </div>
                  <div class="pa-breakdown-row">
                    <span class="pa-breakdown-label">已下架</span>
                    <div class="pa-breakdown-track">
                      <div class="pa-breakdown-fill" :style="{ width: percent(stats.servers.suspended, stats.servers.total), background: '#ef4444' }"></div>
                    </div>
                    <strong>{{ stats.servers.suspended || 0 }}</strong>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <!-- 右列：公告 + 操作日志 -->
          <div class="pa-overview-right">
            <section v-if="hasPerm('platform.announcements.manage')" class="pa-section">
              <div class="pa-section-head">
                <span class="pa-section-title">平台公告</span>
                <router-link class="pa-btn pa-btn-sm pa-btn-outline" to="/platform-admin/announcements">查看全部</router-link>
              </div>
              <div class="pa-list pa-list-dense">
                <article v-for="item in announcements" :key="item.id" class="pa-list-card pa-list-card-sm">
                  <div class="pa-list-main">
                    <div class="pa-card-head">
                      <span :class="['pa-badge', item.is_important ? 'pa-badge-red' : 'pa-badge-gray']">
                        {{ item.is_important ? '重要' : '普通' }}
                      </span>
                      <span :class="['pa-badge', targetBadgeClass(item)]">{{ targetLabel(item) }}</span>
                      <span class="pa-meta">{{ fmtTime(item.created_at) }}</span>
                    </div>
                    <strong class="pa-list-title">{{ s(item.title) }}</strong>
                    <div class="pa-meta">{{ s(item.content).slice(0, 60) }}{{ s(item.content).length > 60 ? '…' : '' }}</div>
                  </div>
                </article>
                <div v-if="!announcements.length" class="pa-empty">暂无公告</div>
              </div>
            </section>

            <section v-if="hasPerm('platform.logs.view')" class="pa-section">
              <div class="pa-section-head">
                <span class="pa-section-title">最近操作</span>
                <span class="pa-section-meta">审计记录</span>
              </div>
              <div class="pa-logs-compact">
                <article v-for="log in operationLogs" :key="log.id" class="pa-log-row">
                  <span :class="['pa-log-dot', logDotClass(log.operation_type)]"></span>
                  <div class="pa-log-body">
                    <span class="pa-log-action">{{ operationLabel(log.operation_type) }}</span>
                    <span class="pa-log-detail">{{ log.details || '无详情' }}</span>
                  </div>
                  <span class="pa-log-time">{{ fmtTime(log.created_at) }}</span>
                </article>
                <div v-if="!operationLogs.length" class="pa-empty">暂无操作日志</div>
              </div>
            </section>
          </div>
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
  getPlatformMe,
  getPlatformStats,
  listAnnouncements,
  listOperationLogs,
} from '@/api/platform'
import './platform-admin.css'

const loading = ref(false)
const me = ref({ is_platform_admin: false, permissions: [] })
const toast = reactive({ message: '', type: 'ok' })
const stats = reactive({
  servers: { total: 0, active: 0, inactive: 0, suspended: 0, pending_audit: 0, public: 0 },
  users: { total_users: 0, platform_admins: 0 },
  restrictions: { total: 0, by_type: {} },
  reports: { total: 0, pending: 0, processing: 0, resolved: 0, ignored: 0 },
})
const announcements = ref([])
const operationLogs = ref([])
const pendingReportCount = computed(() => (stats.reports.pending || 0) + (stats.reports.processing || 0))
const totalTodoCount = computed(() => (stats.servers.pending_audit || 0) + (stats.restrictions.total || 0) + pendingReportCount.value)

function showToast(message, type = 'ok') {
  toast.message = message
  toast.type = type
}

function clearToast() { toast.message = '' }

function s(v) { return v == null ? '' : (typeof v === 'string' ? v : String(v)) }

function hasPerm(perm) {
  if (me.value?.is_platform_admin) return true
  const perms = me.value?.permissions || []
  for (const p of perms) {
    if (p === '*' || p === perm) return true
    if (p.endsWith('.*')) {
      const prefix = p.slice(0, -2)
      if (perm === prefix || perm.startsWith(prefix + '.')) return true
    }
  }
  return false
}

function targetLabel(item) {
  if (!item) return '-'
  if (item.target_type === 'all') return '全局公告'
  if (item.target_type === 'server') return '服务器 #' + (item.server_id ?? '?')
  if (item.target_type === 'account') return '账户 #' + (item.target_account_id ?? '?')
  return item.server_id ? '服务器 #' + item.server_id : '全局公告'
}

function targetBadgeClass(item) {
  if (!item) return 'pa-badge-gray'
  if (item.target_type === 'all') return 'pa-badge-blue'
  if (item.target_type === 'server') return 'pa-badge-green'
  if (item.target_type === 'account') return 'pa-badge-orange'
  return 'pa-badge-gray'
}

function fmtTime(ts) {
  if (!ts || typeof ts !== 'number') return '-'
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

function percent(value, total) {
  const n = Number(value || 0)
  const d = Number(total || 0)
  if (!d) return '0%'
  return `${Math.min(100, Math.max(0, Math.round((n / d) * 100)))}%`
}

function operationLabel(type) {
  return ({
    audit_approve: '审核通过',
    audit_reject: '审核驳回',
    server_update: '服务器更新',
    server_delete: '服务器删除',
    account_ban: '账号限制',
    announcement_create: '发布公告',
    announcement_update: '更新公告',
    announcement_delete: '删除公告',
    permission_grant: '授予权限',
    permission_revoke: '撤销权限',
  })[type] || type || '平台操作'
}

function logDotClass(type) {
  if (type?.startsWith('announcement')) return 'pa-log-dot-blue'
  if (type?.startsWith('audit')) return 'pa-log-dot-green'
  if (type?.startsWith('account') || type?.startsWith('permission')) return 'pa-log-dot-orange'
  if (type?.startsWith('server')) return 'pa-log-dot-purple'
  return ''
}

async function loadAll() {
  loading.value = true
  clearToast()
  try {
    me.value = await getPlatformMe()

    const tasks = []
    if (hasPerm('platform.dashboard.view')) tasks.push(['stats', getPlatformStats()])
    if (hasPerm('platform.announcements.manage')) {
      tasks.push(['announcements', listAnnouncements({ status: 'active', limit: 6 })])
    }
    if (hasPerm('platform.logs.view')) tasks.push(['logs', listOperationLogs({ limit: 8 })])

    const results = await Promise.allSettled(tasks.map(([, task]) => task))
    results.forEach((result, index) => {
      if (result.status !== 'fulfilled') return
      const key = tasks[index][0]
      const value = result.value
      if (key === 'stats') {
        stats.servers = { ...stats.servers, ...(value.servers || {}) }
        stats.users = { ...stats.users, ...(value.users || {}) }
        stats.restrictions = { ...stats.restrictions, ...(value.restrictions || {}) }
        stats.reports = { ...stats.reports, ...(value.reports || {}) }
      }
      if (key === 'announcements') announcements.value = value || []
      if (key === 'logs') operationLogs.value = value || []
    })
  } catch (e) {
    showToast(e.message || '加载概览失败', 'err')
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>
