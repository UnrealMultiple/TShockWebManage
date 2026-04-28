<template>
  <div class="pa-page">
    <PageHeader title="云黑审核" subtitle="审核服务器提交的平台云黑记录">
      <template #actions>
        <button class="pa-btn pa-btn-outline" :disabled="loading" @click="loadItems">
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
        <section class="pa-section">
          <div class="pa-section-head">
            <span class="pa-section-title">提交记录</span>
            <span class="pa-section-meta">本页 {{ items.length }} 条</span>
          </div>

          <div class="pa-subsection">
            <div class="pa-toolbar">
              <div class="pa-toolbar-left">
                <select v-model="filters.status" class="pa-input pa-filter" @change="loadItems">
                  <option value="pending">待审核</option>
                  <option value="approved">已通过</option>
                  <option value="rejected">已拒绝</option>
                  <option value="all">全部状态</option>
                </select>
                <input
                  v-model.trim="filters.q"
                  class="pa-input pa-search"
                  placeholder="搜索账号、服务器、原因或提交人"
                  @keyup.enter="loadItems"
                />
              </div>
              <div class="pa-toolbar-right">
                <button class="pa-btn pa-btn-outline" @click="loadItems">搜索</button>
                <button class="pa-btn pa-btn-outline" @click="resetFilters">重置</button>
              </div>
            </div>
          </div>

          <div class="pa-table-wrap">
            <table class="pa-table">
              <thead>
                <tr>
                  <th>目标账号</th>
                  <th>来源服务器</th>
                  <th>原因</th>
                  <th>状态</th>
                  <th>提交时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in items" :key="item.id">
                  <td>
                    <strong>{{ item.target_email }}</strong>
                    <div class="pa-table-meta">用户 ID：{{ item.target_user_id }}</div>
                  </td>
                  <td>
                    <strong>{{ item.source_server_name || '-' }}</strong>
                    <div class="pa-table-meta">服务器 ID：{{ item.source_server_id }}</div>
                  </td>
                  <td>
                    <div class="pa-table-meta">{{ item.reason || '无原因' }}</div>
                    <div class="pa-table-meta">提交人：{{ item.submitted_by_email || item.submitted_by_user_id }}</div>
                  </td>
                  <td>
                    <span :class="['pa-badge', statusBadge(item.status)]">{{ statusLabel(item.status) }}</span>
                  </td>
                  <td><span class="pa-meta">{{ fmtTime(item.submitted_at) }}</span></td>
                  <td>
                    <div class="pa-split-actions">
                      <template v-if="item.status === 'pending'">
                        <button class="pa-btn pa-btn-sm pa-btn-primary" :disabled="busyId === item.id" @click="review(item.id, 'approve')">通过</button>
                        <button class="pa-btn pa-btn-sm pa-btn-outline" :disabled="busyId === item.id" @click="review(item.id, 'reject')">拒绝</button>
                      </template>
                      <span v-else class="pa-meta">{{ item.review_note || '已审核' }}</span>
                      <button class="pa-btn pa-btn-sm pa-btn-danger" :disabled="busyId === item.id" @click="removeItem(item)">删除</button>
                    </div>
                  </td>
                </tr>
                <tr v-if="!items.length">
                  <td colspan="6" class="pa-empty-row">暂无云黑提交</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import PlatformNav from '@/components/PlatformNav.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useFeedback } from '@/composables/useFeedback'
import {
  deleteCloudBlacklistSubmission,
  listCloudBlacklistSubmissions,
  reviewCloudBlacklistSubmission,
} from '@/api/platform'
import './platform-admin.css'

const loading = ref(false)
const busyId = ref(null)
const items = ref([])
const filters = reactive({ status: 'pending', q: '' })
const toast = reactive({ message: '', type: 'ok' })
const { dialog } = useFeedback()

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

function statusLabel(status) {
  return ({ pending: '待审核', approved: '已通过', rejected: '已拒绝' })[status] || status || '-'
}

function statusBadge(status) {
  return ({ pending: 'pa-badge-yellow', approved: 'pa-badge-green', rejected: 'pa-badge-red' })[status] || 'pa-badge-gray'
}

async function loadItems() {
  loading.value = true
  clearToast()
  try {
    items.value = await listCloudBlacklistSubmissions({ status: filters.status, q: filters.q, limit: 100 })
  } catch (e) {
    showToast(e.message || '加载云黑提交失败', 'err')
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.status = 'pending'
  filters.q = ''
  loadItems()
}

async function review(id, action) {
  const note = action === 'reject'
    ? await dialog.prompt({
        title: '拒绝云黑记录',
        message: '填写拒绝原因。',
        label: '拒绝原因',
        placeholder: '请输入拒绝原因',
        confirmText: '拒绝',
      })
    : ''
  if (action === 'reject' && note === null) return
  busyId.value = id
  try {
    await reviewCloudBlacklistSubmission(id, action, note || '')
    showToast(action === 'approve' ? '云黑记录已通过' : '云黑记录已拒绝')
    await loadItems()
  } catch (e) {
    showToast(e.message || '审核失败', 'err')
  } finally {
    busyId.value = null
  }
}

async function removeItem(item) {
  if (!item?.id) return
  const ok = await dialog.confirm({
    title: '删除云黑记录',
    message: `确定删除「${item.target_email}」的云黑记录吗？`,
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  busyId.value = item.id
  try {
    await deleteCloudBlacklistSubmission(item.id)
    showToast('云黑记录已删除')
    await loadItems()
  } catch (e) {
    showToast(e.message || '删除失败', 'err')
  } finally {
    busyId.value = null
  }
}

onMounted(loadItems)
</script>
