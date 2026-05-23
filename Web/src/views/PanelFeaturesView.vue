<template>
  <div class="cfg-page">
    <PageHeader title="面板功能管理">
      <template #meta>
        <span v-if="hasChanges" class="cfg-modified-badge">● 未保存</span>
      </template>
      <template #actions>
        <button class="cfg-btn cfg-btn-outline" @click="loadSettings" :disabled="loading || !activeServer">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
          </svg>
          刷新
        </button>
        <button class="cfg-btn cfg-btn-primary" @click="saveSettings" :disabled="saving || !hasChanges || !canManage || !activeServer">
          <svg v-if="saving" viewBox="0 0 24 24" class="spinning" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
          {{ saving ? '保存中…' : '保存配置' }}
        </button>
      </template>
    </PageHeader>

    <div v-if="!activeServer" class="cfg-empty">
      <div class="cfg-empty-icon">⚙️</div>
      <p>请先在左侧选择一个服务器</p>
    </div>

    <template v-else>
      <div v-if="loading" class="cfg-loading">
        <div class="cfg-spinner"></div>
        <span>正在加载配置…</span>
      </div>

      <div v-else class="cfg-editor">
        <div v-if="errorMsg" class="cfg-toast cfg-toast-err">
          {{ errorMsg }}
          <button class="cfg-toast-close" @click="errorMsg = ''">✕</button>
        </div>
        <div v-if="okMsg" class="cfg-toast cfg-toast-ok">
          {{ okMsg }}
          <button class="cfg-toast-close" @click="okMsg = ''">✕</button>
        </div>

        <!-- 搜索框：与 TShockConfigView.vue 风格统一 -->
        <div class="cfg-search-bar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input v-model="searchQuery" class="cfg-search-input" placeholder="搜索功能项…" />
          <button v-if="searchQuery" class="cfg-search-clear" @click="searchQuery = ''">✕</button>
        </div>

        <!-- 搜索结果模式 -->
        <div v-if="searchQuery.trim()" class="cfg-search-results">
          <div v-if="filteredFields.length === 0" class="cfg-no-result">没有匹配"{{ searchQuery }}"的功能项</div>
          <template v-else>
            <div v-for="f in filteredFields" :key="f.key" class="cfg-field-row">
              <div class="cfg-field-meta">
                <div class="cfg-field-key">{{ f.label }}</div>
                <div class="cfg-field-desc">{{ f.desc }}</div>
              </div>
              <div class="cfg-field-input-wrap" :class="{ 'cfg-field-input-wrap--wide': f.key === 'character_name_regex' }">
                <template v-if="f.key === 'register_limit'">
                  <input v-model.number="form.register_limit" type="number" min="0" max="50" class="cfg-input" :disabled="saving || !canManage" />
                </template>
                <template v-else-if="f.key === 'character_name_regex'">
                  <input v-model="form.character_name_regex" type="text" maxlength="256" class="cfg-input cfg-input-mono" :disabled="saving || !canManage" />
                </template>
                <template v-else-if="f.key === 'character_name_max_length'">
                  <input v-model.number="form.character_name_max_length" type="number" min="1" max="50" class="cfg-input" :disabled="saving || !canManage" />
                </template>
                <template v-else-if="f.key === 'server_code'">
                  <div class="code-row">
                    <input :value="serverCode" class="cfg-input" disabled />
                    <button class="cfg-copy-btn" @click="copyServerCode">复制</button>
                  </div>
                </template>
                <template v-else-if="f.key === 'join_requires_approval'">
                  <label class="cfg-switch">
                    <input type="checkbox" v-model="form.join_requires_approval" :disabled="saving || !isServerOwner" />
                    <span class="cfg-switch-track"><span class="cfg-switch-thumb"></span></span>
                  </label>
                </template>
                <template v-else-if="f.key === 'blacklist_auto_reject_count'">
                  <input v-model.number="form.blacklist_auto_reject_count" type="number" min="0" max="99" class="cfg-input" :disabled="saving || !canManage" />
                </template>
              </div>
            </div>
          </template>
        </div>

        <!-- 正常模式 -->
        <template v-else>
          <div class="cfg-fields-panel">
            <div class="cfg-field-row cfg-field-row--stack">
              <div class="cfg-field-meta">
                <div class="cfg-field-key">发送邀请</div>
                <div class="cfg-field-desc">向成员 QQ 号发送服务器邀请。</div>
              </div>
              <div class="cfg-field-content">
                <div v-if="!canInvite" class="cfg-empty-mini">当前账号无邀请权限</div>
                <div v-else class="cfg-invite-grid">
                  <div class="cfg-field-group">
                    <label class="cfg-label">被邀请 QQ 号</label>
                    <input v-model="inviteForm.email" class="cfg-input" type="text" maxlength="128" placeholder="123456789" />
                  </div>
                  <div class="cfg-field-group">
                    <label class="cfg-label">附言（可选）</label>
                    <input v-model="inviteForm.message" class="cfg-input" type="text" maxlength="300" placeholder="邀请说明…" />
                  </div>
                  <div class="cfg-field-group cfg-field-group--narrow">
                    <label class="cfg-label">有效期（小时）</label>
                    <input v-model.number="inviteForm.expiresInHours" class="cfg-input" type="number" min="1" max="720" />
                  </div>
                  <div class="cfg-field-group cfg-field-group--action">
                    <label class="cfg-label cfg-label--spacer">&nbsp;</label>
                    <button class="cfg-btn cfg-btn-primary" :disabled="membershipLoading" @click="sendInvite">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                      </svg>
                      发送邀请
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div class="cfg-field-row cfg-field-row--stack">
              <div class="cfg-field-meta">
                <div class="cfg-field-key">待审批申请</div>
                <div class="cfg-field-desc">查看并处理玩家提交的入服申请。</div>
              </div>
              <div class="cfg-field-content">
                <div class="cfg-subsection-label-row">
                  <span v-if="pendingRequests.length" class="cfg-count-badge">{{ pendingRequests.length }}</span>
                  <button v-if="canReview" class="cfg-btn cfg-btn-sm cfg-btn-outline" :disabled="membershipLoading" @click="loadJoinRequests">刷新</button>
                </div>
                <div v-if="!canReview" class="cfg-empty-mini">当前账号无审批权限</div>
                <div v-else-if="!pendingRequests.length" class="cfg-empty-mini">暂无待审批申请</div>
                <div v-else class="cfg-review-list">
                  <div v-for="req in pendingRequests" :key="req.id" class="cfg-review-card">
                    <div class="cfg-review-card-head">
                      <span class="cfg-review-badge">入服申请</span>
                      <span class="cfg-review-time">{{ fmtTime(req.created_at) }}</span>
                    </div>
                    <div class="cfg-review-card-body">
                      <span class="cfg-review-applicant">{{ req.applicant_email }}</span>
                      申请加入服务器
                    </div>
                    <div v-if="req.message" class="cfg-review-meta">附言：{{ req.message }}</div>
                    <details v-if="blacklistDetails(req).length" class="cfg-review-warning">
                      <summary>黑名单提示：{{ blacklistSummary(req) }}</summary>
                      <div class="cfg-blacklist-detail-list">
                        <div v-for="item in blacklistDetails(req)" :key="`${item.scope}-${item.id}`" class="cfg-blacklist-detail">
                          <div class="cfg-blacklist-detail-head">
                            <span>{{ item.label }}</span>
                            <span>{{ fmtTime(item.reviewed_at || item.created_at) }}</span>
                          </div>
                          <div class="cfg-blacklist-reason">{{ item.reason || '未填写原因' }}</div>
                          <div class="cfg-blacklist-meta">
                            <span v-if="item.source_server_name">来源：{{ item.source_server_name }}</span>
                            <span v-if="item.operator_email">提交人：{{ item.operator_email }}</span>
                            <span v-if="item.review_note">审核备注：{{ item.review_note }}</span>
                          </div>
                        </div>
                      </div>
                    </details>
                    <div class="cfg-review-note-row">
                      <input
                        v-model="reviewNotes[req.id]"
                        class="cfg-input cfg-input-sm"
                        placeholder="审批备注（可选，将通知申请人）"
                      />
                    </div>
                    <div class="cfg-review-actions">
                      <button class="cfg-btn cfg-btn-sm cfg-btn-primary" :disabled="membershipLoading" @click="approveRequest(req.id)">批准</button>
                      <button class="cfg-btn cfg-btn-sm cfg-btn-outline" :disabled="membershipLoading" @click="rejectRequest(req.id)">拒绝</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="cfg-field-row">
              <div class="cfg-field-meta">
                <div class="cfg-field-key">每个账户最大注册角色数量</div>
                <div class="cfg-field-desc">限制单个面板账号可绑定的游戏角色数量，0 表示禁止创建新角色。</div>
              </div>
              <div class="cfg-field-input-wrap">
                <input v-model.number="form.register_limit" type="number" min="0" max="50" class="cfg-input" :disabled="saving || !canManage" />
              </div>
            </div>

            <div class="cfg-field-row">
              <div class="cfg-field-meta">
                <div class="cfg-field-key">玩家注册名字正则</div>
                <div class="cfg-field-desc">注册和绑定角色时使用该规则校验玩家名字。</div>
              </div>
              <div class="cfg-field-input-wrap cfg-field-input-wrap--wide">
                <input v-model="form.character_name_regex" type="text" maxlength="256" class="cfg-input cfg-input-mono" :disabled="saving || !canManage" />
              </div>
            </div>

            <div class="cfg-field-row">
              <div class="cfg-field-meta">
                <div class="cfg-field-key">玩家名字最大长度</div>
                <div class="cfg-field-desc">限制玩家注册名字最多可填写的字符数。</div>
              </div>
              <div class="cfg-field-input-wrap">
                <input v-model.number="form.character_name_max_length" type="number" min="1" max="50" class="cfg-input" :disabled="saving || !canManage" />
              </div>
            </div>

            <div class="cfg-field-row">
              <div class="cfg-field-meta">
                <div class="cfg-field-key">服务器编号</div>
                <div class="cfg-field-desc">供成员提交入服申请时填写。</div>
              </div>
              <div class="cfg-field-input-wrap">
                <div class="code-row">
                  <input :value="serverCode" class="cfg-input" disabled />
                  <button class="cfg-copy-btn" @click="copyServerCode">复制</button>
                </div>
              </div>
            </div>

            <div class="cfg-field-row">
              <div class="cfg-field-meta">
                <div class="cfg-field-key">加入申请审核</div>
                <div class="cfg-field-desc">开启后需要管理员审批。</div>
              </div>
              <div class="cfg-field-input-wrap">
                <label class="cfg-switch">
                  <input type="checkbox" v-model="form.join_requires_approval" :disabled="saving || !isServerOwner" />
                  <span class="cfg-switch-track"><span class="cfg-switch-thumb"></span></span>
                </label>
              </div>
            </div>

            <div class="cfg-field-row">
              <div class="cfg-field-meta">
                <div class="cfg-field-key">云黑自动拒绝阈值</div>
                <div class="cfg-field-desc">云黑记录达到该数量时自动拒绝入服申请，0 表示关闭。</div>
              </div>
              <div class="cfg-field-input-wrap">
                <input v-model.number="form.blacklist_auto_reject_count" type="number" min="0" max="99" class="cfg-input" :disabled="saving || !canManage" />
              </div>
            </div>
          </div>
        </template>

        <p v-if="!canManage" class="cfg-note">当前账号无权限修改此配置。</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, inject, ref, watch } from 'vue'
import {
  getPanelFeatures,
  updatePanelFeatures,
  updateJoinApproval,
  listPanelJoinRequests,
  approvePanelJoinRequest,
  rejectPanelJoinRequest,
  createPanelInvite,
} from '@/api/servers'
import { normalizeQqEmailInput, qqEmailInputError } from '@/utils/qqEmail'
import PageHeader from '@/components/PageHeader.vue'

const activeServer = inject('activeServer', ref(null))
const canManage = inject('canManageActiveServer', ref(false))
const hasPerm = inject('hasPerm', (() => false))
const isServerOwner = inject('isServerOwner', ref(false))

const loading = ref(false)
const saving = ref(false)
const errorMsg = ref('')
const okMsg = ref('')

const DEFAULT_CHARACTER_NAME_REGEX = '^[\\u4e00-\\u9fffA-Za-z0-9:/\\[\\]]+$'
const DEFAULT_CHARACTER_NAME_MAX_LENGTH = 20

const form = ref({
  register_limit: 1,
  join_requires_approval: false,
  blacklist_auto_reject_count: 0,
  character_name_regex: DEFAULT_CHARACTER_NAME_REGEX,
  character_name_max_length: DEFAULT_CHARACTER_NAME_MAX_LENGTH,
})
const originalLimit = ref(1)
const originalJoinApproval = ref(false)
const originalBlacklistAutoRejectCount = ref(0)
const originalCharacterNameRegex = ref(DEFAULT_CHARACTER_NAME_REGEX)
const originalCharacterNameMaxLength = ref(DEFAULT_CHARACTER_NAME_MAX_LENGTH)
const serverCode = ref('')
const membershipLoading = ref(false)
const pendingRequests = ref([])
const inviteForm = ref({ email: '', message: '', expiresInHours: 72 })
const reviewNotes = ref({})   // requestId → note string
const searchQuery = ref('')

// 搜索功能项配置
const featureFields = [
  { key: 'register_limit', label: '每个账户最大注册角色数量', desc: '限制单个面板账号可绑定的游戏角色数量，0 表示禁止创建新角色。' },
  { key: 'character_name_regex', label: '玩家注册名字正则', desc: '注册和绑定角色时使用该规则校验玩家名字。' },
  { key: 'character_name_max_length', label: '玩家名字最大长度', desc: '限制玩家注册名字最多可填写的字符数。' },
  { key: 'server_code', label: '服务器编号', desc: '供成员提交入服申请时填写。' },
  { key: 'join_requires_approval', label: '加入申请审核', desc: '开启后需要管理员审批。' },
  { key: 'blacklist_auto_reject_count', label: '云黑自动拒绝阈值', desc: '云黑记录达到该数量时自动拒绝入服申请，0 表示关闭。' },
]

const filteredFields = computed(() => {
  const q = String(searchQuery.value || '').trim().toLowerCase()
  if (!q) return []
  return featureFields.filter(f => 
    f.label.toLowerCase().includes(q) || f.desc.toLowerCase().includes(q)
  )
})

const hasChanges = computed(() => {
  const limitChanged = Number(form.value.register_limit) !== Number(originalLimit.value)
  const joinApprovalChanged = Boolean(form.value.join_requires_approval) !== Boolean(originalJoinApproval.value)
  const blacklistChanged = Number(form.value.blacklist_auto_reject_count) !== Number(originalBlacklistAutoRejectCount.value)
  const nameRegexChanged = normalizeCharacterNameRegex(form.value.character_name_regex) !== String(originalCharacterNameRegex.value)
  const nameMaxLengthChanged = Number(form.value.character_name_max_length) !== Number(originalCharacterNameMaxLength.value)
  return limitChanged || joinApprovalChanged || blacklistChanged || nameRegexChanged || nameMaxLengthChanged
})

const canReview = computed(() => !!isServerOwner.value || hasPerm('panel.membership.review') || hasPerm('panel.users'))
const canInvite = computed(() => !!isServerOwner.value || hasPerm('panel.invites.manage') || hasPerm('panel.membership.review') || hasPerm('panel.users'))
const canReviewOrInvite = computed(() => canReview.value || canInvite.value)

function fmtTime(ts) {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleString()
}

function blacklistDetails(req) {
  return Array.isArray(req?.blacklist_details) ? req.blacklist_details : []
}

function blacklistSummary(req) {
  const local = Number(req?.server_blacklist_count || 0)
  const cloud = Number(req?.cloud_blacklist_count || 0)
  const parts = []
  if (local) parts.push(`本服务器黑名单 ${local} 条`)
  if (cloud) parts.push(`平台云黑 ${cloud} 条`)
  return parts.join(' / ') || '有黑名单记录'
}

async function copyServerCode() {
  if (!serverCode.value) return
  const ok = await copyToClipboard(serverCode.value)
  if (ok) {
    okMsg.value = '服务器编号已复制'
    errorMsg.value = ''
  } else {
    errorMsg.value = '复制失败，请手动复制'
  }
}

async function copyToClipboard(text) {
  const value = String(text || '')
  if (!value) return false
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value)
      return true
    }
  } catch {
    // 继续尝试兼容方案
  }

  try {
    const ta = document.createElement('textarea')
    ta.value = value
    ta.setAttribute('readonly', '')
    ta.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0;pointer-events:none'
    document.body.appendChild(ta)
    ta.focus()
    ta.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  } catch {
    return false
  }
}

async function loadJoinRequests() {
  const sid = activeServer.value?.id
  if (!sid || !canReview.value) {
    pendingRequests.value = []
    return
  }
  membershipLoading.value = true
  try {
    pendingRequests.value = await listPanelJoinRequests(sid, 'pending')
  } catch (e) {
    errorMsg.value = e.message || '加载申请失败'
  } finally {
    membershipLoading.value = false
  }
}

async function sendInvite() {
  const sid = activeServer.value?.id
  if (!sid || !canInvite.value) return
  const email = normalizeQqEmailInput(inviteForm.value.email)
  if (!email) {
    errorMsg.value = qqEmailInputError('被邀请用户 QQ 号')
    return
  }
  membershipLoading.value = true
  try {
    await createPanelInvite(sid, email, inviteForm.value.message || '', Number(inviteForm.value.expiresInHours || 72))
    inviteForm.value.email = ''
    inviteForm.value.message = ''
    okMsg.value = '邀请已发送'
  } catch (e) {
    errorMsg.value = e.message || '发送邀请失败'
  } finally {
    membershipLoading.value = false
  }
}

async function approveRequest(requestId) {
  const sid = activeServer.value?.id
  if (!sid || !canReview.value) return
  const note = reviewNotes.value[requestId] || ''
  membershipLoading.value = true
  try {
    await approvePanelJoinRequest(sid, requestId, note)
    okMsg.value = '已批准申请'
    delete reviewNotes.value[requestId]
    await loadJoinRequests()
  } catch (e) {
    errorMsg.value = e.message || '审批失败'
  } finally {
    membershipLoading.value = false
  }
}

async function rejectRequest(requestId) {
  const sid = activeServer.value?.id
  if (!sid || !canReview.value) return
  const note = reviewNotes.value[requestId] || ''
  membershipLoading.value = true
  try {
    await rejectPanelJoinRequest(sid, requestId, note)
    okMsg.value = '已拒绝申请'
    delete reviewNotes.value[requestId]
    await loadJoinRequests()
  } catch (e) {
    errorMsg.value = e.message || '拒绝失败'
  } finally {
    membershipLoading.value = false
  }
}

function normalizeLimit(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return 1
  return Math.max(0, Math.min(50, Math.round(n)))
}

function normalizeBlacklistThreshold(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return 0
  return Math.max(0, Math.min(99, Math.round(n)))
}

function normalizeCharacterNameMaxLength(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return DEFAULT_CHARACTER_NAME_MAX_LENGTH
  return Math.max(1, Math.min(50, Math.round(n)))
}

function normalizeCharacterNameRegex(v) {
  const pattern = String(v || '').trim()
  return pattern || DEFAULT_CHARACTER_NAME_REGEX
}

watch(() => form.value.register_limit, (v) => {
  const normalized = normalizeLimit(v)
  if (normalized !== v) form.value.register_limit = normalized
})

watch(() => form.value.blacklist_auto_reject_count, (v) => {
  const normalized = normalizeBlacklistThreshold(v)
  if (normalized !== v) form.value.blacklist_auto_reject_count = normalized
})

watch(() => form.value.character_name_max_length, (v) => {
  const normalized = normalizeCharacterNameMaxLength(v)
  if (normalized !== v) form.value.character_name_max_length = normalized
})

async function loadSettings() {
  const sid = activeServer.value?.id
  if (!sid) return
  loading.value = true
  errorMsg.value = ''
  okMsg.value = ''
  try {
    const data = await getPanelFeatures(sid)
    const limit = normalizeLimit(data.register_limit)
    originalLimit.value = limit
    form.value.register_limit = limit
    const joinApproval = !!data.join_requires_approval
    originalJoinApproval.value = joinApproval
    form.value.join_requires_approval = joinApproval
    const threshold = normalizeBlacklistThreshold(data.blacklist_auto_reject_count)
    originalBlacklistAutoRejectCount.value = threshold
    form.value.blacklist_auto_reject_count = threshold
    const nameRegex = normalizeCharacterNameRegex(data.character_name_regex)
    originalCharacterNameRegex.value = nameRegex
    form.value.character_name_regex = nameRegex
    const nameMaxLength = normalizeCharacterNameMaxLength(data.character_name_max_length)
    originalCharacterNameMaxLength.value = nameMaxLength
    form.value.character_name_max_length = nameMaxLength
    serverCode.value = String(data.server_code || '')
    await loadJoinRequests()
  } catch (e) {
    errorMsg.value = e.message || '加载配置失败'
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  const sid = activeServer.value?.id
  if (!sid || !canManage.value) return
  saving.value = true
  errorMsg.value = ''
  okMsg.value = ''
  try {
    const nameRegex = normalizeCharacterNameRegex(form.value.character_name_regex)
    const payload = {
      register_limit: normalizeLimit(form.value.register_limit),
      blacklist_auto_reject_count: normalizeBlacklistThreshold(form.value.blacklist_auto_reject_count),
      character_name_regex: nameRegex,
      character_name_max_length: normalizeCharacterNameMaxLength(form.value.character_name_max_length),
    }
    const data = await updatePanelFeatures(sid, payload)
    if (Boolean(form.value.join_requires_approval) !== Boolean(originalJoinApproval.value)) {
      await updateJoinApproval(sid, !!form.value.join_requires_approval)
    }
    const limit = normalizeLimit(data.register_limit)
    originalLimit.value = limit
    form.value.register_limit = limit
    const threshold = normalizeBlacklistThreshold(data.blacklist_auto_reject_count)
    originalBlacklistAutoRejectCount.value = threshold
    form.value.blacklist_auto_reject_count = threshold
    const savedNameRegex = normalizeCharacterNameRegex(data.character_name_regex)
    originalCharacterNameRegex.value = savedNameRegex
    form.value.character_name_regex = savedNameRegex
    const savedNameMaxLength = normalizeCharacterNameMaxLength(data.character_name_max_length)
    originalCharacterNameMaxLength.value = savedNameMaxLength
    form.value.character_name_max_length = savedNameMaxLength
    originalJoinApproval.value = !!form.value.join_requires_approval
    serverCode.value = String(data.server_code || serverCode.value)
    okMsg.value = '配置已保存'
  } catch (e) {
    errorMsg.value = e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

watch(() => activeServer.value?.id, (id) => {
  if (id) loadSettings()
  else {
    form.value.register_limit = 1
    form.value.join_requires_approval = false
    form.value.blacklist_auto_reject_count = 0
    form.value.character_name_regex = DEFAULT_CHARACTER_NAME_REGEX
    form.value.character_name_max_length = DEFAULT_CHARACTER_NAME_MAX_LENGTH
    originalLimit.value = 1
    originalJoinApproval.value = false
    originalBlacklistAutoRejectCount.value = 0
    originalCharacterNameRegex.value = DEFAULT_CHARACTER_NAME_REGEX
    originalCharacterNameMaxLength.value = DEFAULT_CHARACTER_NAME_MAX_LENGTH
    serverCode.value = ''
    pendingRequests.value = []
    errorMsg.value = ''
    okMsg.value = ''
  }
}, { immediate: true })
</script>

<style scoped>
/* ══════════════════════════════════════════════
   页面基础布局
══════════════════════════════════════════════ */
.cfg-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: #f8fafc;
}

.cfg-modified-badge {
  font-size: 12px;
  color: #d97706;
  background: #fef3c7;
  border: 1px solid #fde68a;
  border-radius: 20px;
  padding: 2px 8px;
  animation: pulse-dot 1.5s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50%       { opacity: .5; }
}

/* ── 编辑器主区 ── */
.cfg-editor {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* ── 搜索框：与 TShockConfigView.vue 风格统一 ── */
.cfg-search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px 8px;
  flex-shrink: 0;
}

.cfg-search-bar svg {
  width: 16px;
  height: 16px;
  color: #94a3b8;
  flex-shrink: 0;
}

.cfg-search-input {
  flex: 1;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
  outline: none;
  background: #fff;
  color: #1e293b;
  transition: border-color 0.15s;
}

.cfg-search-input:focus {
  border-color: #3b82f6;
}

.cfg-search-clear {
  background: none;
  border: none;
  cursor: pointer;
  color: #94a3b8;
  font-size: 14px;
  padding: 4px;
}

.cfg-search-clear:hover {
  color: #64748b;
}

/* ── 搜索结果区 ── */
.cfg-search-results {
  flex: 1;
  overflow-y: auto;
  padding: 8px 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cfg-no-result {
  text-align: center;
  padding: 40px;
  color: #94a3b8;
  font-size: 14px;
}

/* ── Toast 通知 ── */
.cfg-toast {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 12px 24px 0;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  flex-shrink: 0;
}

.cfg-toast-ok  { background: #dcfce7; border: 1px solid #bbf7d0; color: #166534; }
.cfg-toast-err { background: #fee2e2; border: 1px solid #fecaca; color: #991b1b; }

.cfg-toast-close {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 14px;
  opacity: .6;
  padding: 0 0 0 12px;
}

.cfg-toast-close:hover { opacity: 1; }

/* ── 功能字段面板 ── */
.cfg-fields-panel {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cfg-fields-panel > .cfg-section {
  margin: 0 0 8px;
}

.cfg-field-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
}

.cfg-field-row--stack {
  align-items: stretch;
  flex-direction: column;
}

.cfg-field-meta { min-width: 0; flex: 1; }

.cfg-field-content {
  min-width: 0;
  width: 100%;
}

.cfg-field-key {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.cfg-field-desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.45;
  color: #64748b;
}

.cfg-field-input-wrap {
  width: 140px;
  flex-shrink: 0;
}

.cfg-field-input-wrap--wide {
  width: min(420px, 45vw);
}

/* ── 服务器编号行 ── */
.code-row { display: flex; align-items: center; gap: 8px; }

.cfg-copy-btn {
  border: 1px solid #d1d5db;
  background: #fff;
  color: #374151;
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.cfg-copy-btn:hover { background: #f8fafc; }

/* ── Toggle switch ── */
.cfg-switch { display: inline-flex; align-items: center; cursor: pointer; }
.cfg-switch input { position: absolute; opacity: 0; width: 0; height: 0; }

.cfg-switch-track {
  position: relative;
  width: 40px;
  height: 22px;
  background: #e2e8f0;
  border-radius: 11px;
  transition: background .2s;
}

.cfg-switch input:checked + .cfg-switch-track { background: #3b82f6; }

.cfg-switch-thumb {
  position: absolute;
  top: 3px; left: 3px;
  width: 16px; height: 16px;
  border-radius: 50%;
  background: #fff;
  transition: transform .2s;
  box-shadow: 0 1px 3px rgba(0,0,0,.18);
}

.cfg-switch input:checked + .cfg-switch-track .cfg-switch-thumb { transform: translateX(18px); }

/* ══════════════════════════════════════════════
   邀请 & 审批 区块
══════════════════════════════════════════════ */
.cfg-section {
  margin: 0 24px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
  overflow: hidden;
}

.cfg-section-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  background: #f8fafc;
}

.cfg-section-title {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

/* ── 子区块 ── */
.cfg-subsection {
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
}

.cfg-subsection:last-child { border-bottom: none; }

.cfg-subsection-label {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 10px;
}

.cfg-subsection-label-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.cfg-count-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 7px;
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
}

/* ── 邀请表单网格 ── */
.cfg-invite-grid {
  display: grid;
  grid-template-columns: 1.2fr 1.3fr 130px auto;
  gap: 10px;
  align-items: end;
}

.cfg-field-group { display: flex; flex-direction: column; gap: 5px; }
.cfg-field-group--narrow { max-width: 130px; }
.cfg-field-group--action { flex-shrink: 0; }

.cfg-label {
  font-size: 11px;
  font-weight: 500;
  color: #64748b;
}

.cfg-label--spacer { visibility: hidden; }

/* ── 申请审批列表 ── */
.cfg-review-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cfg-review-card {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px;
  background: #fff;
  transition: border-color 0.15s;
}

.cfg-review-card:hover { border-color: #94a3b8; }

.cfg-review-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.cfg-review-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  background: #faf5ff;
  color: #6d28d9;
  border: 1px solid #ddd6fe;
}

.cfg-review-time {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
}

.cfg-review-card-body {
  font-size: 13px;
  color: #334155;
  line-height: 1.55;
  margin-bottom: 6px;
}

.cfg-review-applicant {
  font-weight: 600;
  color: #0f172a;
  margin-right: 6px;
}

.cfg-review-meta {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 8px;
}

.cfg-review-warning {
  margin-bottom: 8px;
  padding: 7px 9px;
  border: 1px solid #fbbf24;
  border-radius: 8px;
  background: #fffbeb;
  color: #92400e;
  font-size: 12px;
  line-height: 1.45;
}

.cfg-review-warning summary {
  cursor: pointer;
  font-weight: 600;
}

.cfg-blacklist-detail-list {
  display: grid;
  gap: 8px;
  margin-top: 8px;
}

.cfg-blacklist-detail {
  padding-top: 8px;
  border-top: 1px solid #fde68a;
}

.cfg-blacklist-detail-head,
.cfg-blacklist-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.cfg-blacklist-detail-head {
  justify-content: space-between;
  color: #78350f;
  font-weight: 600;
}

.cfg-blacklist-reason {
  margin-top: 4px;
  color: #451a03;
  white-space: pre-wrap;
}

.cfg-blacklist-meta {
  margin-top: 4px;
  color: #92400e;
}

.cfg-review-note-row {
  margin-bottom: 10px;
}

.cfg-review-actions {
  display: flex;
  gap: 8px;
}

.cfg-empty-mini {
  font-size: 13px;
  color: #94a3b8;
  padding: 10px 0 4px;
}

.cfg-empty-mini--section {
  padding: 14px 16px;
}

/* ── 输入框 ── */
.cfg-input {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 13px;
  color: #0f172a;
  background: #fff;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.cfg-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,.12);
}

.cfg-input-sm { padding: 6px 10px; font-size: 12px; }
.cfg-input-mono { font-family: Consolas, "Courier New", monospace; }

/* ── 按钮 ── */
.cfg-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
  white-space: nowrap;
}

.cfg-btn svg { width: 14px; height: 14px; flex-shrink: 0; }
.cfg-btn:disabled { opacity: 0.45; cursor: not-allowed; }

.cfg-btn-sm { padding: 5px 12px; font-size: 12px; }

.cfg-btn-primary { background: #3b82f6; color: #fff; }
.cfg-btn-primary:hover:not(:disabled) { background: #2563eb; }

.cfg-btn-outline {
  background: #fff;
  border: 1px solid #d1d5db;
  color: #374151;
}
.cfg-btn-outline:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #9ca3af;
}

.spinning { animation: spin .7s linear infinite; }

/* ── 权限提示 ── */
.cfg-note {
  margin: 0 24px 20px;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fcd34d;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
}

/* ── 空态 / 加载态 ── */
.cfg-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  text-align: center;
  color: #94a3b8;
  padding: 60px 24px;
  font-size: 14px;
}

.cfg-empty-icon { font-size: 40px; }

.cfg-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 12px;
  padding: 60px 24px;
  font-size: 14px;
  color: #64748b;
}

.cfg-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin .7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ── 响应式 ── */
@media (max-width: 768px) {
  .cfg-fields-panel { padding: 12px 14px 20px; }
  .cfg-section { margin: 0 14px 14px; }
  .cfg-toast { margin: 10px 14px 0; }
  .cfg-note  { margin: 0 14px 16px; }
  .cfg-search-bar { padding: 10px 14px 6px; }
  .cfg-search-results { padding: 6px 14px 16px; }

  .cfg-field-row { flex-direction: column; align-items: stretch; }
  .cfg-field-input-wrap { width: 100%; }

  .cfg-invite-grid { grid-template-columns: 1fr; }
  .cfg-field-group--narrow { max-width: 100%; }

  .cfg-review-card-head { flex-wrap: wrap; }
}
</style>
