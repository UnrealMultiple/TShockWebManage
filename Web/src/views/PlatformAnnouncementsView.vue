<template>
  <div class="pa-page">
    <PageHeader title="公告管理" subtitle="创建、编辑与归档平台公告">
      <template #actions>
        <button class="pa-btn pa-btn-outline" :disabled="loading" @click="loadAll">
          {{ loading ? '刷新中' : '刷新' }}
        </button>
        <button class="pa-btn pa-btn-primary" @click="openCreate">+ 新建公告</button>
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
            <span class="pa-section-title">公告列表</span>
            <span class="pa-section-meta">共 {{ pagination.total }} 条，本页 {{ announcements.length }} 条</span>
          </div>

          <div class="pa-subsection">
            <div class="pa-toolbar">
              <div class="pa-toolbar-left">
                <select v-model="filters.target_type" class="pa-input pa-filter">
                  <option value="">全部范围</option>
                  <option value="all">全局公告</option>
                  <option value="server">指定服务器</option>
                  <option value="account">指定账户</option>
                </select>
                <select v-model="filters.is_important" class="pa-input pa-filter">
                  <option value="">全部等级</option>
                  <option value="true">重要公告</option>
                  <option value="false">普通公告</option>
                </select>
                <select v-model="filters.status" class="pa-input pa-filter">
                  <option value="active">仅生效</option>
                  <option value="archived">仅归档</option>
                </select>
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
                  <th>标题</th>
                  <th>范围</th>
                  <th>等级</th>
                  <th>状态</th>
                  <th>创建时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in announcements" :key="item.id">
                  <td>
                    <strong>{{ s(item.title) }}</strong>
                    <div class="pa-table-meta">{{ s(item.content).slice(0, 60) }}{{ s(item.content).length > 60 ? '…' : '' }}</div>
                  </td>
                  <td>
                    <span :class="['pa-badge', targetBadgeClass(item)]">{{ targetLabel(item) }}</span>
                  </td>
                  <td>
                    <span :class="['pa-badge', item.is_important ? 'pa-badge-red' : 'pa-badge-gray']">
                      {{ item.is_important ? '重要' : '普通' }}
                    </span>
                  </td>
                  <td>
                    <span :class="['pa-badge', item.status === 'active' ? 'pa-badge-green' : 'pa-badge-gray']">
                      {{ item.status === 'active' ? '生效中' : '已归档' }}
                    </span>
                  </td>
                  <td>
                    <span class="pa-meta">{{ fmtTime(item.created_at) }}</span>
                  </td>
                  <td>
                    <div class="pa-split-actions">
                      <button class="pa-btn pa-btn-sm pa-btn-outline" @click="openEdit(item)">编辑</button>
                      <button v-if="item.status === 'active'" class="pa-btn pa-btn-sm pa-btn-outline" @click="archiveAnnouncement(item.id)">归档</button>
                      <button class="pa-btn pa-btn-sm pa-btn-danger" @click="removeAnnouncement(item.id)">删除</button>
                    </div>
                  </td>
                </tr>
                <tr v-if="!announcements.length">
                  <td colspan="6" class="pa-empty-row">暂无公告数据</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="pa-pagination">
            <button class="pa-btn pa-btn-sm pa-btn-outline" :disabled="pagination.page <= 1 || loading" @click="goPage(pagination.page - 1)">
              上一页
            </button>
            <span class="pa-meta">{{ pagination.page }} / {{ totalPages }} 页，共 {{ pagination.total }} 条</span>
            <button class="pa-btn pa-btn-sm pa-btn-outline" :disabled="pagination.page >= totalPages || loading" @click="goPage(pagination.page + 1)">
              下一页
            </button>
          </div>
        </section>
      </div>
    </div>

    <!-- 新建/编辑公告模态框 -->
    <div v-if="showEditor" class="pa-modal-overlay" @click.self="closeEditor">
      <div class="pa-modal">
        <div class="pa-modal-head">
          <h3>{{ editingId ? '编辑公告' : '新建公告' }}</h3>
          <button class="pa-toast-close" @click="closeEditor">x</button>
        </div>
        <div class="pa-modal-body">
          <div class="pa-form-grid">
            <div class="pa-subsection-label">发送范围</div>
            <div class="pa-radio-bar">
              <label :class="['pa-radio-chip', { 'pa-radio-chip--active': form.target_type === 'all' }]">
                <input v-model="form.target_type" type="radio" value="all" />
                所有账户
              </label>
              <label :class="['pa-radio-chip', { 'pa-radio-chip--active': form.target_type === 'server' }]">
                <input v-model="form.target_type" type="radio" value="server" />
                指定服务器
              </label>
              <label :class="['pa-radio-chip', { 'pa-radio-chip--active': form.target_type === 'account' }]">
                <input v-model="form.target_type" type="radio" value="account" />
                指定账户
              </label>
            </div>
            <div class="pa-range-hint">
              <template v-if="form.target_type === 'all'">平台全体用户可见</template>
              <template v-else-if="form.target_type === 'server'">仅该服务器拥有「接收服务器公告」权限的用户可见</template>
              <template v-else>仅该账户本人可见</template>
            </div>

            <div v-if="form.target_type === 'server'">
              <select v-model.number="form.server_id" class="pa-input">
                <option :value="null" disabled>请选择服务器</option>
                <option v-for="sv in serverList" :key="sv.id" :value="sv.id">{{ sv.name }} (ID: {{ sv.id }})</option>
              </select>
            </div>
            <div v-if="form.target_type === 'account'">
              <input v-model.number="form.target_account_id" type="number" class="pa-input" placeholder="输入目标账户 ID" />
            </div>

            <input
              v-model.trim="form.title"
              :class="['pa-input', { 'pa-input-error': formError && !form.title }]"
              placeholder="公告标题"
              @input="formError = ''"
            />
            <textarea
              v-model.trim="form.content"
              :class="['pa-input', { 'pa-input-error': formError && !form.content }]"
              rows="5"
              placeholder="公告内容"
              @input="formError = ''"
            ></textarea>
            <div v-if="formError" class="pa-form-error">{{ formError }}</div>
            <div class="pa-inline-form">
              <label class="pa-checkline"><input v-model="form.is_important" type="checkbox" />标记为重要公告</label>
            </div>
          </div>
        </div>
        <div class="pa-modal-foot">
          <button class="pa-btn pa-btn-outline" @click="closeEditor">取消</button>
          <button class="pa-btn pa-btn-primary" :disabled="saving" @click="submitForm">
            {{ saving ? '提交中…' : editingId ? '更新公告' : '发布公告' }}
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
import { useFeedback } from '@/composables/useFeedback'
import {
  createAnnouncement,
  deleteAnnouncement,
  listAnnouncements,
  listPlatformServers,
  updateAnnouncement,
} from '@/api/platform'
import './platform-admin.css'

const loading = ref(false)
const saving = ref(false)
const announcements = ref([])
const serverList = ref([])
const toast = reactive({ message: '', type: 'ok' })
const { dialog } = useFeedback()
const filters = reactive({ target_type: '', is_important: '', status: 'active' })
const pagination = reactive({ page: 1, limit: 20, total: 0 })
const showEditor = ref(false)
const editingId = ref(null)
const formError = ref('')
const form = reactive({ target_type: 'all', server_id: null, target_account_id: null, title: '', content: '', is_important: false })

const totalPages = computed(() => Math.max(1, Math.ceil((pagination.total || 0) / pagination.limit)))

function showToast(message, type = 'ok') {
  toast.message = String(message ?? '')
  toast.type = String(type ?? 'ok')
}
function clearToast() { toast.message = '' }

function s(v) { return v == null ? '' : (typeof v === 'string' ? v : String(v)) }

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

function buildQuery() {
  const q = { skip: (pagination.page - 1) * pagination.limit, limit: pagination.limit }
  if (filters.target_type) q.target_type = filters.target_type
  if (filters.is_important) q.is_important = filters.is_important === 'true'
  if (filters.status) q.status = filters.status
  return q
}

async function loadAll() {
  loading.value = true
  clearToast()
  try {
    const annData = await listAnnouncements(buildQuery())
    announcements.value = Array.isArray(annData) ? annData : (annData?.items || [])
    const got = announcements.value.length
    pagination.total = got < pagination.limit ? (pagination.page - 1) * pagination.limit + got : 999
  } catch (e) {
    showToast(String(e?.message || e?.detail || e || '加载公告失败'), 'err')
  } finally {
    loading.value = false
  }
  // 服务器列表独立加载，失败不影响公告
  try {
    const srvData = await listPlatformServers({ limit: 200 })
    serverList.value = Array.isArray(srvData?.items) ? srvData.items : (Array.isArray(srvData) ? srvData : [])
  } catch {
    serverList.value = []
  }
}

function applyFilters() {
  pagination.page = 1
  loadAll()
}

function resetFilters() {
  Object.assign(filters, { target_type: '', is_important: '', status: 'active' })
  applyFilters()
}

function goPage(page) {
  pagination.page = page
  loadAll()
}

function openCreate() {
  editingId.value = null
  formError.value = ''
  Object.assign(form, { target_type: 'all', server_id: null, target_account_id: null, title: '', content: '', is_important: false })
  showEditor.value = true
}

function openEdit(item) {
  editingId.value = item.id
  formError.value = ''
  form.target_type = item.target_type || 'all'
  form.server_id = item.server_id || null
  form.target_account_id = item.target_account_id || null
  form.title = item.title || ''
  form.content = item.content || ''
  form.is_important = !!item.is_important
  showEditor.value = true
}

function closeEditor() {
  formError.value = ''
  showEditor.value = false
}

async function submitForm() {
  if (!form.title || !form.content) {
    formError.value = '必填项不能为空'
    return
  }
  if (form.target_type === 'server' && !form.server_id) { showToast('请选择目标服务器', 'err'); return }
  if (form.target_type === 'account' && !form.target_account_id) { showToast('请输入目标账户ID', 'err'); return }

  const payload = {
    title: form.title,
    content: form.content,
    target_type: form.target_type,
    is_important: form.is_important,
  }
  if (form.target_type === 'server') payload.server_id = form.server_id
  if (form.target_type === 'account') payload.target_account_id = form.target_account_id

  saving.value = true
  try {
    const result = editingId.value
      ? await updateAnnouncement(editingId.value, payload)
      : await createAnnouncement(payload)
    closeEditor()
    const count = Number(result?.notification?.receiver_count || 0)
    showToast(editingId.value ? '公告已更新' : (count > 0 ? `公告已发布，已通知 ${count} 个账号` : '公告已发布，暂无可通知账号'))
    await loadAll()
  } catch (e) {
    showToast(String(e?.message || e?.detail || e || '提交失败'), 'err')
  } finally {
    saving.value = false
  }
}

async function archiveAnnouncement(id) {
  try {
    await updateAnnouncement(id, {
      title: announcements.value.find(a => a.id === id)?.title || '',
      content: announcements.value.find(a => a.id === id)?.content || '',
      target_type: announcements.value.find(a => a.id === id)?.target_type || 'all',
      is_important: !!announcements.value.find(a => a.id === id)?.is_important,
    })
    showToast('公告已归档')
    await loadAll()
  } catch (e) {
    showToast(String(e?.message || e?.detail || e || '归档失败'), 'err')
  }
}

async function removeAnnouncement(id) {
  const ok = await dialog.confirm({
    title: '删除公告',
    message: '确定删除此公告？已发送到用户视野中的公告通知也会同步移除。',
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  try {
    await deleteAnnouncement(id)
    showToast('公告已删除')
    await loadAll()
  } catch (e) {
    showToast(String(e?.message || e?.detail || e || '删除失败'), 'err')
  }
}

onMounted(loadAll)
</script>
