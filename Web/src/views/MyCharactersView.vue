<template>
  <div class="mc-page">
    <div class="page-header">
      <h1 class="page-title">我的游戏角色</h1>
      <button class="btn btn-sm btn-outline" @click="loadCharacters" :disabled="loadingChars">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/></svg>
        {{ loadingChars ? '加载中…' : '刷新' }}
      </button>
    </div>

    <div v-if="!activeKey" class="hint-box">
      <div class="hint-icon">🎮</div>
      <p>请先在左侧选择一个服务器</p>
    </div>

    <div v-else class="mc-body">

      <!-- 左侧：表单区 -->
      <div class="mc-forms">

      <!-- ① 注册游戏账号（置顶） -->
      <div class="section-card">
        <div class="section-title">注册游戏账号</div>
        <div class="reg-notice">
          注册后可使用此用户名和密码在游戏内登录服务器（SSC 模式）
        </div>

        <div v-if="!agentOnline" class="warn-box">
          ⚠️ 服务器 Agent 未连接，无法完成注册
        </div>

        <div class="reg-form" :class="{ disabled: !agentOnline }">
          <div class="field-row">
            <label class="field-label">游戏用户名</label>
            <input
              class="field-input"
              v-model="regUsername"
              placeholder="在游戏内使用的名字"
              :disabled="regLoading || !agentOnline"
              maxlength="64"
              @keyup.enter="submitRegister"
            />
          </div>
          <div class="field-row">
            <label class="field-label">登录密码</label>
            <input
              class="field-input"
              type="password"
              v-model="regPassword"
              placeholder="至少 6 位，不能是常见弱密码"
              :disabled="regLoading || !agentOnline"
              maxlength="64"
              @keyup.enter="submitRegister"
            />
          </div>
          <div v-if="regMsg" :class="['reg-msg', regSuccess ? 'reg-ok' : 'reg-err']">
            {{ regMsg }}
          </div>
          <button
            class="btn btn-primary reg-btn"
            :disabled="regLoading || !agentOnline || !regUsername.trim() || regPassword.length < 1"
            @click="submitRegister"
          >
            {{ regLoading ? '注册中…' : '提交注册' }}
          </button>
        </div>
      </div>

      <!-- ② 绑定已有游戏账号 -->
      <div class="section-card">
        <div class="section-title">绑定已有游戏账号</div>
        <div class="reg-notice">
          游戏内已有角色但未与面板绑定？填写角色名，系统将向该角色发送验证码（必须该角色本人在线且已登录）
        </div>

        <div v-if="!agentOnline" class="warn-box">
          ⚠️ 服务器 Agent 未连接，无法发送验证码
        </div>

        <template v-else>
          <!-- Step 1：输入用户名 -->
          <div v-if="!bindCodeSent" class="reg-form">
            <div class="field-row">
              <label class="field-label">游戏用户名</label>
              <input
                class="field-input"
                v-model="bindUsername"
                placeholder="游戏内已有的账号名"
                :disabled="bindLoading"
                maxlength="64"
                @keyup.enter="sendBindCode"
              />
            </div>
            <div v-if="bindMsg" :class="['reg-msg', bindSuccess ? 'reg-ok' : 'reg-err']">
              {{ bindMsg }}
            </div>
            <button
              class="btn btn-primary reg-btn"
              :disabled="bindLoading || !bindUsername.trim()"
              @click="sendBindCode"
            >
              {{ bindLoading ? '发送中…' : '📨 发送验证码' }}
            </button>
          </div>

          <!-- Step 2：输入验证码 -->
          <div v-else class="reg-form">
            <div class="bind-step2-hint">
              ✅ 验证码已发送给游戏内玩家
              <strong>{{ bindUsername }}</strong>，请在游戏聊天栏查看并填入
            </div>
            <div class="field-row">
              <label class="field-label">验证码</label>
              <input
                class="field-input"
                v-model="bindCode"
                placeholder="6 位验证码"
                :disabled="bindVerifyLoading"
                maxlength="10"
                @keyup.enter="verifyBindCode"
              />
            </div>
            <div v-if="bindVerifyMsg" :class="['reg-msg', bindVerifySuccess ? 'reg-ok' : 'reg-err']">
              {{ bindVerifyMsg }}
            </div>
            <div class="bind-btn-row">
              <button
                class="btn btn-primary"
                :disabled="bindVerifyLoading || !bindCode.trim()"
                @click="verifyBindCode"
              >
                {{ bindVerifyLoading ? '验证中…' : '✅ 确认绑定' }}
              </button>
              <button class="btn btn-outline" @click="resetBind">重新发送</button>
            </div>
          </div>
        </template>
      </div>

      </div><!-- /mc-forms -->

      <!-- 右侧：角色列表 -->
      <div class="mc-list">
      <div class="section-card list-card">
        <div class="list-card-header">
          <div class="section-title" style="margin-bottom:0">已绑定角色</div>
          <span class="char-count" v-if="characters.length">共 {{ characters.length }} 个</span>
        </div>
        <div v-if="loadingChars" class="chars-loading">加载中…</div>
        <div v-else-if="!characters.length" class="chars-empty">
          暂无已绑定角色，请在左侧注册或绑定
        </div>
        <div v-else class="char-list">
          <div v-for="c in characters" :key="c.character_name" class="char-row">
            <div class="char-avatar">{{ c.character_name[0]?.toUpperCase() }}</div>
            <div class="char-info">
              <span class="char-name">{{ c.character_name }}</span>
              <span class="char-date">注册于 {{ formatTime(c.registered_at) }}</span>
            </div>
            <!-- 权限组 badge -->
            <span class="char-tag group-tag" :class="groupClass(c.character_name)">
              {{ charInfo[c.character_name]?.loading ? '…' : (charInfo[c.character_name]?.group || '游戏账号') }}
            </span>
            <div class="char-actions">
              <!-- 查看背包按钮 -->
              <button
                class="btn btn-xs btn-outline-info"
                :disabled="!props.agentOnline"
                @click="openInventory(c.character_name)"
                title="查看背包"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg>
                背包
              </button>
              <!-- 改密码 -->
              <template v-if="changePassTarget === c.character_name">
                <input
                  class="field-input inline-pass-input"
                  type="password"
                  v-model="changePassNewPwd"
                  placeholder="新密码（6位+）"
                  maxlength="64"
                  @keyup.enter="submitChangePassword"
                />
                <button class="btn btn-xs btn-primary"
                  :disabled="changePassLoading || changePassNewPwd.length < 6"
                  @click="submitChangePassword">
                  {{ changePassLoading ? '修改中…' : '确认' }}
                </button>
                <button class="btn btn-xs btn-outline" @click="changePassTarget = null; changePassNewPwd = ''; changePassMsg = ''">取消</button>
                <span v-if="changePassMsg" :class="['inline-msg', changePassOk ? 'msg-ok' : 'msg-err']">{{ changePassMsg }}</span>
              </template>
              <button v-else class="btn btn-xs btn-outline"
                :disabled="!props.agentOnline"
                @click="changePassTarget = c.character_name; changePassNewPwd = ''; changePassMsg = ''">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                改密码
              </button>
              <template v-if="deleteConfirm[c.character_name]">
                <span class="del-confirm-text">确认删除？</span>
                <button class="btn btn-xs btn-danger" :disabled="deleteLoading[c.character_name]"
                  @click="confirmDelete(c.character_name)">
                  {{ deleteLoading[c.character_name] ? '删除中…' : '确认' }}
                </button>
                <button class="btn btn-xs btn-outline" @click="deleteConfirm[c.character_name] = false">取消</button>
              </template>
              <button v-else class="btn btn-xs btn-outline-danger"
                @click="deleteConfirm[c.character_name] = true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
                删除
              </button>
            </div>
          </div>
        </div>
      </div>

      </div><!-- /mc-list -->

    </div><!-- /mc-body -->

    <!-- 背包弹窗 -->
    <InventoryModal
      :show="invVisible"
      :username="invUsername"
      :loading="invLoading"
      :error="invError"
      :slots="invSlots"
      :health="invHealth"
      :max-health="invMaxHealth"
      :mana="invMana"
      :max-mana="invMaxMana"
      :is-online="invIsOnline"
      :can-edit="false"
      @close="invVisible = false"
    />

  </div>
</template>

<script setup>
import { ref, computed, inject, watch, onMounted, onUnmounted } from 'vue'
import { getToken } from '@/api/auth'
import { deleteMyCharacter } from '@/api/servers'
import { apiUrl } from '@/api/base'
import InventoryModal from '@/components/InventoryModal.vue'
import { useInventory } from '@/composables/useInventory'

const myServers    = inject('myServers', ref([]))
const activeKey    = inject('activeServerKey', ref(''))
const activeServer = inject('activeServer', ref(null))

const props = defineProps({
  agentOnline: { type: Boolean, default: false },
})

// ── 角色列表 ──────────────────────────────────────────────────────
const characters  = ref([])
const loadingChars = ref(false)
const serverIdCache = ref(null)

// charInfo: { [charName]: { loading, group, ssc_enabled, has_ssc_data, inventory } }
const charInfo = ref({})
// reqMap: { [msgId]: charName }  —— 用于匹配 WS 回包
const reqMap = ref({})

async function loadCharacters() {
  const srv = myServers.value.find(s => s.agent_key === activeKey.value)
  if (!srv) return
  serverIdCache.value = srv.id
  loadingChars.value = true
  charInfo.value = {}
  try {
    const res = await fetch(apiUrl(`/api/servers/${srv.id}/my-characters`), {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!res.ok) throw new Error((await res.json()).detail || '请求失败')
    characters.value = await res.json()
    // 如果 Agent 在线，立即请求每个角色的权限组 + 背包信息
    if (props.agentOnline) {
      for (const c of characters.value) fetchCharInfo(c.character_name)
    }
  } catch (e) {
    console.warn('[MyChars] 加载失败:', e.message)
  } finally {
    loadingChars.value = false
  }
}

function fetchCharInfo(charName) {
  const msgId = Math.random().toString(36).slice(2)
  reqMap.value[msgId] = charName
  charInfo.value[charName] = { loading: true, group: null, ssc_enabled: false, has_ssc_data: false, inventory: [] }
  window.__tshockSend?.({
    type:      'get_char_info',
    msg_id:    msgId,
    timestamp: Date.now(),
    payload:   { agent_key: activeKey.value, username: charName },
  })
  setTimeout(() => {
    if (charInfo.value[charName]?.loading) {
      charInfo.value[charName] = { ...charInfo.value[charName], loading: false, group: '未知' }
      delete reqMap.value[msgId]
    }
  }, 8000)
}

// 权限组对应样式
function groupClass(charName) {
  const g = charInfo.value[charName]?.group ?? ''
  if (g === 'superadmin' || g === 'owner') return 'tag-superadmin'
  if (g === 'admin') return 'tag-admin'
  if (g === 'vip') return 'tag-vip'
  if (g === 'default' || g === 'guest' || g === '') return 'tag-default'
  return 'tag-custom'
}

watch(activeKey, () => { if (activeKey.value) loadCharacters() }, { immediate: true })

// ── 改密码 ────────────────────────────────────────────────
const changePassTarget  = ref(null)   // 当前正在改密码的角色名
const changePassNewPwd  = ref('')
const changePassMsg     = ref('')
const changePassOk      = ref(false)
const changePassLoading = ref(false)
let   changePassReqId   = null

function submitChangePassword() {
  if (!changePassTarget.value || changePassNewPwd.value.length < 6) return
  changePassLoading.value = true
  changePassMsg.value     = ''
  changePassReqId = Math.random().toString(36).slice(2)
  window.__tshockSend?.({
    type:      'change_password',
    msg_id:    changePassReqId,
    timestamp: Date.now(),
    payload:   { agent_key: activeKey.value, username: changePassTarget.value, new_password: changePassNewPwd.value },
  })
  setTimeout(() => {
    if (changePassLoading.value) {
      changePassLoading.value = false
      changePassMsg.value = '请求超时，请检查 Agent 连接'
      changePassOk.value  = false
      changePassReqId     = null
    }
  }, 10000)
}

// ── 删除角色 ──────────────────────────────────────────────────────
const deleteConfirm = ref({})
const deleteLoading = ref({})

async function confirmDelete(charName) {
  const srv = myServers.value.find(s => s.agent_key === activeKey.value)
  if (!srv) return
  deleteLoading.value[charName] = true
  try {
    await deleteMyCharacter(srv.id, charName)
    deleteConfirm.value[charName] = false
    await loadCharacters()
  } catch (e) {
    alert('删除失败: ' + e.message)
    deleteConfirm.value[charName] = false
  } finally {
    deleteLoading.value[charName] = false
  }
}

// ── 背包弹窗 ──────────────────────────────────────────────────────
const {
  invVisible, invUsername, invLoading, invError,
  invSlots, invHealth, invMaxHealth, invMana, invMaxMana,
  invIsOnline,
  openInventory: _openInv,
  consumeWsMessage: consumeInvMsg,
} = useInventory()
function openInventory(name) { _openInv(name, activeKey.value) }

// ── 绑定已有账号 ──────────────────────────────────────────────────────
const bindUsername       = ref('')
const bindCode           = ref('')
const bindMsg            = ref('')
const bindSuccess        = ref(false)
const bindLoading        = ref(false)
const bindCodeSent       = ref(false)
const bindVerifyMsg      = ref('')
const bindVerifySuccess  = ref(false)
const bindVerifyLoading  = ref(false)
let   bindReqId          = null

function sendBindCode() {
  if (!bindUsername.value.trim() || !activeKey.value || !props.agentOnline) return
  bindLoading.value = true
  bindMsg.value = ''
  bindReqId = Math.random().toString(36).slice(2)
  window.__tshockSend?.({
    type:      'send_bind_code',
    msg_id:    bindReqId,
    timestamp: Date.now(),
    payload:   { agent_key: activeKey.value, username: bindUsername.value.trim() },
  })
  setTimeout(() => {
    if (bindLoading.value) {
      bindLoading.value = false
      bindMsg.value = '请求超时，请确认该角色在线且已登录账号'
      bindSuccess.value = false
      bindReqId = null
    }
  }, 10000)
}

async function verifyBindCode() {
  if (!bindCode.value.trim()) return
  const srv = myServers.value.find(s => s.agent_key === activeKey.value)
  if (!srv) return
  bindVerifyLoading.value = true
  bindVerifyMsg.value = ''
  try {
    const res = await fetch(apiUrl(`/api/servers/${srv.id}/bind-verify`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify({ username: bindUsername.value.trim(), code: bindCode.value.trim() }),
    })
    const data = await res.json()
    if (!res.ok) {
      bindVerifyMsg.value = data.detail || '验证失败'
      bindVerifySuccess.value = false
    } else {
      bindVerifyMsg.value = '绑定成功！'
      bindVerifySuccess.value = true
      setTimeout(() => { resetBind(); loadCharacters() }, 1500)
    }
  } catch (e) {
    bindVerifyMsg.value = '网络错误: ' + e.message
    bindVerifySuccess.value = false
  } finally {
    bindVerifyLoading.value = false
  }
}

function resetBind() {
  bindCodeSent.value = false
  bindCode.value = ''
  bindVerifyMsg.value = ''
  bindMsg.value = ''
  bindReqId = null
}

// ── 注册表单 ──────────────────────────────────────────────────────
const regUsername = ref('')
const regPassword = ref('')
const regMsg      = ref('')
const regSuccess  = ref(false)
const regLoading  = ref(false)
let   regReqId    = null

function submitRegister() {
  if (!regUsername.value.trim() || !regPassword.value) return
  if (!activeKey.value || !props.agentOnline) {
    regMsg.value = 'Agent 未连接'
    regSuccess.value = false
    return
  }
  regLoading.value = true
  regMsg.value = ''
  regReqId = Math.random().toString(36).slice(2)
  window.__tshockSend?.({
    type:      'register_user',
    msg_id:    regReqId,
    timestamp: Date.now(),
    payload:   {
      agent_key: activeKey.value,
      username:  regUsername.value.trim(),
      password:  regPassword.value,
    },
  })
  setTimeout(() => {
    if (regLoading.value) {
      regLoading.value = false
      regMsg.value = '请求超时，请检查 Agent 连接'
      regSuccess.value = false
      regReqId = null
    }
  }, 10000)
}

function onWsMessage(e) {
  const pkt = e.detail
  if (!pkt) return

  // 注册回执
  if (pkt.type === 'register_user_resp') {
    const p = pkt.payload || {}
    if (p.ref_id !== regReqId) return
    regLoading.value = false
    regReqId = null
    regSuccess.value = !!p.success
    regMsg.value = p.msg || (p.success ? '注册成功！' : '注册失败')
    if (p.success) {
      regUsername.value = ''
      regPassword.value = ''
      loadCharacters()
    }
    return
  }

  // 绑定验证码发送回执
  if (pkt.type === 'send_bind_code_resp') {
    const p = pkt.payload || {}
    if (p.ref_id !== bindReqId) return
    bindLoading.value = false
    bindReqId = null
    bindSuccess.value = !!p.success
    bindMsg.value = p.msg || (p.success ? '验证码已发送' : '发送失败')
    if (p.success) bindCodeSent.value = true
    return
  }

  // 改密码回执
  if (pkt.type === 'change_password_resp') {
    const p = pkt.payload || {}
    if (p.ref_id !== changePassReqId) return
    changePassLoading.value = false
    changePassReqId         = null
    changePassOk.value      = !!p.success
    changePassMsg.value     = p.msg || (p.success ? '密码已更新' : '修改失败')
    if (p.success) {
      changePassNewPwd.value = ''
      setTimeout(() => { changePassTarget.value = null; changePassMsg.value = '' }, 2000)
    }
    return
  }

  // 角色信息回执
  if (pkt.type === 'get_char_info_resp') {
    const p = pkt.payload || {}
    const charName = reqMap.value[p.ref_id]
    if (!charName) return
    delete reqMap.value[p.ref_id]
    charInfo.value[charName] = {
      loading:      false,
      group:        p.group        ?? 'guest',
      ssc_enabled:  p.ssc_enabled  ?? false,
      has_ssc_data: p.has_ssc_data ?? false,
    }
    return
  }

  // 背包数据回执
  if (consumeInvMsg(pkt)) return
}

onMounted(() => window.addEventListener('ws-message', onWsMessage))
onUnmounted(() => window.removeEventListener('ws-message', onWsMessage))

function formatTime(ts) {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.mc-page {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 20px 24px;
  box-sizing: border-box;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-shrink: 0;
}

/* ── 左右双列布局 ─────────────────────────────────────── */
.mc-body {
  display: flex;
  gap: 20px;
  flex: 1;
  min-height: 0;
}

.mc-forms {
  width: 360px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  padding-right: 4px;
}

.mc-list {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.list-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  margin-bottom: 0 !important;
}

.list-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  flex-shrink: 0;
}

.char-count {
  font-size: .78rem;
  color: #94a3b8;
  background: #f1f5f9;
  padding: 2px 8px;
  border-radius: 20px;
}

.page-title {
  font-size: 1.35rem;
  font-weight: 700;
  margin: 0;
  color: #0f172a;
}

.hint-box {
  text-align: center;
  padding: 60px 20px;
  color: #64748b;
}
.hint-icon { font-size: 2.5rem; margin-bottom: 12px; }

/* ── 卡片 ────────────────────────────────────────────── */
.section-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px 24px;
}

.section-title {
  font-size: .9rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: .06em;
  margin-bottom: 16px;
}

/* ── 角色列表 ─────────────────────────────────────────── */
.chars-loading, .chars-empty {
  text-align: center;
  padding: 24px;
  color: #94a3b8;
  font-size: .88rem;
}

.char-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-right: 2px;
}

.char-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 9px;
}

.char-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6c63ff, #a78bfa);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1rem;
  flex-shrink: 0;
}

.char-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.char-name {
  font-weight: 600;
  font-size: .92rem;
  color: #0f172a;
}

.char-date {
  font-size: .78rem;
  color: #94a3b8;
}

.char-tag {
  background: rgba(108,99,255,.1);
  color: #6c63ff;
  font-size: .72rem;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 20px;
}

.group-tag { font-size: .72rem; font-weight: 600; padding: 3px 8px; border-radius: 20px; }
.tag-superadmin { background: rgba(239,68,68,.12); color: #dc2626; }
.tag-admin      { background: rgba(245,158,11,.12); color: #d97706; }
.tag-vip        { background: rgba(16,185,129,.12); color: #059669; }
.tag-default    { background: rgba(100,116,139,.1); color: #64748b; }
.tag-custom     { background: rgba(108,99,255,.1);  color: #6c63ff; }

.btn-outline-info {
  background: transparent;
  border: 1px solid #bae6fd;
  color: #0284c7;
  cursor: pointer;
  border-radius: 6px;
  padding: 3px 9px;
  font-size: .75rem;
  transition: background .15s;
}
.btn-outline-info:hover:not(:disabled) { background: #f0f9ff; }
.btn-outline-info:disabled { opacity: .45; cursor: not-allowed; }

/* ── 背包弹窗 ──────────────────────────────────────────── */
.inv-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15,23,42,.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.inv-dialog {
  background: #fff;
  border-radius: 14px;
  width: min(680px, 96vw);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 24px 48px rgba(0,0,0,.18);
}

.inv-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  font-weight: 700;
  font-size: .95rem;
  color: #0f172a;
}

.inv-close {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  color: #64748b;
  line-height: 1;
  padding: 2px 6px;
  border-radius: 4px;
  transition: background .15s;
}
.inv-close:hover { background: #f1f5f9; }

.inv-body {
  overflow-y: auto;
  padding: 16px 20px;
  flex: 1;
}

.inv-notice {
  text-align: center;
  padding: 32px 0;
  color: #94a3b8;
  font-size: .88rem;
}

.inv-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 8px;
}

.inv-slot {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  cursor: default;
}

.inv-name {
  font-size: .8rem;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.inv-stack {
  font-size: .72rem;
  color: #94a3b8;
}

.char-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  flex-wrap: wrap;
}
.inline-pass-input {
  width: 130px;
  padding: 3px 8px;
  font-size: .82rem;
  height: 28px;
}
.inline-msg {
  font-size: .78rem;
  font-weight: 500;
}
.msg-ok  { color: #16a34a; }
.msg-err { color: #b91c1c; }

.del-confirm-text {
  font-size: .78rem;
  color: #b91c1c;
  font-weight: 500;
}

.btn-xs {
  padding: 3px 9px;
  font-size: .75rem;
  border-radius: 6px;
}

.btn-danger {
  background: #ef4444;
  color: #fff;
  border: none;
}
.btn-danger:hover:not(:disabled) { background: #dc2626; }

.btn-outline-danger {
  background: transparent;
  border: 1px solid #fca5a5;
  color: #dc2626;
  cursor: pointer;
  border-radius: 6px;
  padding: 3px 9px;
  font-size: .75rem;
  transition: background .15s;
}
.btn-outline-danger:hover { background: #fef2f2; }

/* ── 注册表单 ─────────────────────────────────────────── */
.reg-notice {
  font-size: .84rem;
  color: #64748b;
  margin-bottom: 16px;
  line-height: 1.5;
}

.warn-box {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 10px 14px;
  color: #92400e;
  font-size: .85rem;
  margin-bottom: 14px;
}

.reg-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.reg-form.disabled { opacity: .6; pointer-events: none; }

.field-row {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field-label {
  font-size: .82rem;
  font-weight: 500;
  color: #374151;
}

.field-input {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 9px 12px;
  font-size: .88rem;
  color: #0f172a;
  background: #fff;
  outline: none;
  transition: border-color .15s;
}
.field-input:focus { border-color: #6c63ff; box-shadow: 0 0 0 3px rgba(108,99,255,.12); }
.field-input::placeholder { color: #94a3b8; }
.field-input:disabled { background: #f1f5f9; color: #94a3b8; }

.reg-msg {
  font-size: .84rem;
  padding: 8px 12px;
  border-radius: 7px;
}
.reg-ok { background: #f0fdf4; color: #15803d; border: 1px solid #86efac; }
.reg-err { background: #fef2f2; color: #b91c1c; border: 1px solid #fca5a5; }

.reg-btn { align-self: flex-start; }

/* ── 按钮 ────────────────────────────────────────────── */
.btn {
  display: inline-flex; align-items: center; gap: 6px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: .85rem;
  font-weight: 500;
  padding: 8px 18px;
  transition: opacity .15s, transform .1s;
}
.btn:hover:not(:disabled) { opacity: .88; transform: translateY(-1px); }
.btn:disabled { opacity: .45; cursor: not-allowed; transform: none; }
.btn-primary { background: #6c63ff; color: #fff; }
.btn-outline  { background: transparent; border: 1px solid #d1d5db; color: #374151; }
.btn-sm { padding: 5px 12px; font-size: .8rem; }

/* ── 绑定功能 ─────────────────────────────────────────── */
.bind-step2-hint {
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: .84rem;
  color: #15803d;
  line-height: 1.5;
}
.bind-btn-row {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
