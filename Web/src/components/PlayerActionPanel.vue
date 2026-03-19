<template>
  <!-- 玩家操作面板 - 可复用于仪表盘/用户管理/成员管理 -->
  <transition name="pap-fade">
    <div v-if="show" class="pap-overlay" @click.self="$emit('close')">
      <div class="pap-panel">

        <!-- ── 标题栏 ── -->
        <div class="pap-header">
          <div class="pap-header-left">
            <div class="pap-avatar" :style="{ background: avatarBg }">{{ (playerName || '?')[0].toUpperCase() }}</div>
            <div>
              <div class="pap-title">{{ playerName }}</div>
              <div class="pap-badges">
                <span :class="['pap-badge', isOnline ? 'badge-online' : 'badge-offline']">
                  <span class="dot"></span>{{ isOnline ? '在线' : '离线' }}
                </span>
                <span v-if="group" class="pap-badge badge-group">{{ group }}</span>
                <span v-if="email" class="pap-badge badge-email">{{ email }}</span>
              </div>
            </div>
          </div>
          <button class="pap-close" @click="$emit('close')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="15" height="15"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>

        <div class="pap-body">

          <!-- ── 基础信息区 ── -->
          <div class="pap-section">
            <div class="pap-section-title">玩家信息</div>
            <div class="pap-info-grid">
              <div class="pap-info-item">
                <span class="info-label">角色名</span>
                <span class="info-val">{{ playerName }}</span>
              </div>
              <div v-if="email" class="pap-info-item">
                <span class="info-label">绑定邮箱</span>
                <span class="info-val">{{ email }}</span>
              </div>
              <div class="pap-info-item">
                <span class="info-label">游戏权限组</span>
                <span class="info-val">{{ group || 'default' }}</span>
              </div>
              <div v-if="isOnline" class="pap-info-item">
                <span class="info-label">血量</span>
                <span class="info-val">{{ hp }} / {{ maxHp }}</span>
              </div>
              <div v-if="isOnline" class="pap-info-item">
                <span class="info-label">魔力</span>
                <span class="info-val">{{ mana }} / {{ maxMana }}</span>
              </div>
            </div>
          </div>

          <!-- ── 背包入口 ── -->
          <div class="pap-section">
            <div class="pap-section-title">背包 &amp; 角色数据</div>
            <button class="pap-action-btn btn-primary-outline" :disabled="!agentOnline" @click="$emit('open-inventory', playerName)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg>
              查看背包 / 物品详情
            </button>
          </div>

          <!-- ── 快捷操作 ── -->
          <div class="pap-section">
            <div class="pap-section-title">快捷操作</div>
            <div class="pap-actions-grid">

              <!-- 给予物品 -->
              <div class="pap-action-group">
                <button class="pap-action-btn btn-neutral" :disabled="!agentOnline || !isOnline"
                  @click="giveItemOpen = !giveItemOpen" title="只有在线玩家才能接收物品">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M21 10H3"/><path d="M16 6l5 4-5 4"/><path d="M3 6v12a2 2 0 0 0 2 2h14"/></svg>
                  给予物品
                </button>
                <transition name="pap-slide">
                  <div v-if="giveItemOpen" class="pap-inline-form">
                    <input v-model="giveItemQuery" type="text" placeholder="物品ID 或 名称" class="pap-input" />
                    <input v-model.number="giveItemStack" type="number" min="1" max="9999" placeholder="数量" class="pap-input pap-input-sm" />
                    <button class="pap-confirm-btn" :disabled="!giveItemQuery.trim() || actionBusy" @click="doGiveItem">给予</button>
                  </div>
                </transition>
              </div>

              <!-- 踢出 -->
              <button class="pap-action-btn btn-warn" :disabled="!agentOnline || !isOnline || actionBusy" @click="doAction('kick')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                踢出
              </button>

              <!-- 禁言 / 解禁 -->
              <button class="pap-action-btn btn-warn" :disabled="!agentOnline || !isOnline || actionBusy"
                @click="doAction(isMuted ? 'unmute' : 'mute')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13">
                  <path v-if="!isMuted" d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path v-if="!isMuted" d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                  <line v-if="isMuted" x1="1" y1="1" x2="23" y2="23"/><path v-if="isMuted" d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"/><path v-if="isMuted" d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"/>
                </svg>
                {{ isMuted ? '解除禁言' : '禁言' }}
              </button>

              <!-- 修改权限组 -->
              <div class="pap-action-group">
                <button class="pap-action-btn btn-neutral" :disabled="!agentOnline || actionBusy"
                  @click="toggleSetGroup">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                  修改权限组
                </button>
                <transition name="pap-slide">
                  <div v-if="setGroupOpen" class="pap-inline-form">
                    <select v-if="availableGroups.length" v-model="newGroup" class="pap-input">
                      <option value="" disabled>选择权限组</option>
                      <option v-for="g in availableGroups" :key="g" :value="g">{{ g }}</option>
                    </select>
                    <select v-else-if="groupsLoading" class="pap-input" disabled>
                      <option>获取权限组中…</option>
                    </select>
                    <input v-else v-model="newGroup" placeholder="填入组名，如 admin / vip" class="pap-input" @keyup.enter="doAction('setgroup', { group: newGroup })" />
                    <button class="pap-confirm-btn" :disabled="!newGroup.trim() || actionBusy || groupsLoading" @click="doAction('setgroup', { group: newGroup })">确认</button>
                  </div>
                </transition>
              </div>

            </div>
          </div>

          <!-- ── 危险操作 ── -->
          <div class="pap-section pap-section-danger">
            <div class="pap-section-title danger-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              危险操作
            </div>

            <div class="pap-ban-form">
              <div class="pap-ban-form-row">
                <input v-model="banReason" class="pap-input" type="text" placeholder="封禁原因（默认：由管理员操作）" />
                <select v-model="banDurationPreset" class="pap-input">
                  <option value="permanent">永久封禁</option>
                  <option value="h1">1 小时</option>
                  <option value="h12">12 小时</option>
                  <option value="d1">1 天</option>
                  <option value="d3">3 天</option>
                  <option value="d7">7 天</option>
                  <option value="d30">30 天</option>
                  <option value="custom">自定义</option>
                </select>
              </div>
              <div v-if="banDurationPreset === 'custom'" class="pap-ban-form-row" style="margin-top:8px;">
                <input v-model="banDurationCustom" class="pap-input" type="text" placeholder="自定义时长，如 10d30m0s" />
              </div>
            </div>

            <!-- 封禁 -->
            <div class="pap-action-group">
              <div class="pap-danger-row">
                <template v-if="!banConfirm">
                  <button :class="['pap-action-btn', props.isBanned ? 'btn-success-outline' : 'btn-danger']"
                    :disabled="!agentOnline || actionBusy"
                    @click="banConfirm = true">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
                    {{ props.isBanned ? '解封玩家' : '封禁玩家' }}
                  </button>
                </template>
                <template v-else>
                  <span class="pap-confirm-tip">确认{{ props.isBanned ? '解封' : '封禁' }} {{ playerName }}？</span>
                  <button :class="['pap-confirm-btn', !props.isBanned ? 'btn-danger-sm' : '']" :disabled="actionBusy" @click="confirmBanOrUnban">
                    确认{{ props.isBanned ? '解封' : '封禁' }}
                  </button>
                  <button class="pap-cancel-btn" @click="banConfirm = false">取消</button>
                </template>
              </div>
              <!-- 封禁账号下所有角色（一键）-->
              <div class="pap-danger-row" style="margin-top:6px">
                <template v-if="!banAllConfirm">
                  <button class="pap-action-btn btn-danger-outline" :disabled="!agentOnline || actionBusy || !canBanAll"
                    :title="canBanAll ? '封禁该邮箱账号下绑定的所有游戏角色' : '需要知道绑定邮箱才能一键封禁'"
                    @click="banAllConfirm = true">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
                    一键封禁该账号所有角色
                  </button>
                </template>
                <template v-else>
                  <span class="pap-confirm-tip danger">封禁 {{ email }} 下所有角色？</span>
                  <button class="pap-confirm-btn btn-danger-sm" :disabled="actionBusy" @click="doBanAll">确认全封</button>
                  <button class="pap-cancel-btn" @click="banAllConfirm = false">取消</button>
                </template>
              </div>
              <!-- 解封账号下所有角色（一键）-->
              <div class="pap-danger-row" style="margin-top:6px">
                <template v-if="!unbanAllConfirm">
                  <button class="pap-action-btn btn-success-outline" :disabled="!agentOnline || actionBusy || !canBanAll"
                    :title="canBanAll ? '解封该邮箱账号下绑定的所有游戏角色' : '需要知道绑定邮箱才能一键解封'"
                    @click="unbanAllConfirm = true">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="10"/></svg>
                    一键解封该账号所有角色
                  </button>
                </template>
                <template v-else>
                  <span class="pap-confirm-tip">解封 {{ email }} 下所有角色？</span>
                  <button class="pap-confirm-btn" :disabled="actionBusy" @click="doUnbanAll">确认全解封</button>
                  <button class="pap-cancel-btn" @click="unbanAllConfirm = false">取消</button>
                </template>
              </div>
            </div><!-- /pap-action-group -->

            <!-- 添加到黑名单（留空占位） -->
            <button class="pap-action-btn btn-danger-outline" disabled title="功能待完善">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="18" y1="8" x2="23" y2="13"/><line x1="23" y1="8" x2="18" y2="13"/></svg>
              添加到黑名单（待完善）
            </button>
          </div>

          <!-- ── 结果提示 ── -->
          <transition name="pap-msg">
            <div v-if="resultMsg" :class="['pap-result', resultOk ? 'result-ok' : 'result-err']">
              <svg v-if="resultOk" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="14" height="14"><polyline points="20 6 9 17 4 12"/></svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              {{ resultMsg }}
            </div>
          </transition>

        </div><!-- /pap-body -->
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  show:        { type: Boolean, default: false },
  playerName:  { type: String,  default: '' },
  email:       { type: String,  default: '' },   // 绑定邮箱（可空）
  group:       { type: String,  default: '' },
  isOnline:    { type: Boolean, default: false },
  isMuted:     { type: Boolean, default: false },
  hp:          { type: Number,  default: 0 },
  maxHp:       { type: Number,  default: 0 },
  mana:        { type: Number,  default: 0 },
  maxMana:     { type: Number,  default: 0 },
  agentOnline: { type: Boolean, default: false },
  sscEnabled:  { type: Boolean, default: false },
  // 该邮箱账号下所有绑定角色名列表（用于一键封禁）
  allChars:    { type: Array,   default: () => [] },
  isBanned:    { type: Boolean, default: false },
  banTicket:   { type: Number,  default: 0 },
})

const emit = defineEmits(['close', 'open-inventory', 'action', 'ban-all', 'request-groups'])

// ── 本地 UI 状态 ──────────────────────────────────────────────────
const banConfirm     = ref(false)
const banAllConfirm  = ref(false)
const unbanAllConfirm = ref(false)
const giveItemOpen  = ref(false)
const setGroupOpen  = ref(false)
const giveItemQuery   = ref('')
const giveItemStack   = ref(1)
const newGroup        = ref('')
const availableGroups = ref([])
const groupsLoading   = ref(false)
const actionBusy    = ref(false)
const resultMsg     = ref('')
const resultOk      = ref(true)
const banReason     = ref('')
const banDurationPreset = ref('permanent')
const banDurationCustom = ref('')
let resultTimer     = null

// 重置面板状态
watch(() => props.show, (v) => {
  if (!v) return
  banConfirm.value     = false
  banAllConfirm.value  = false
  unbanAllConfirm.value = false
  giveItemOpen.value  = false
  setGroupOpen.value  = false
  giveItemQuery.value = ''
  giveItemStack.value = 1
  newGroup.value      = props.group || ''
  availableGroups.value = []
  groupsLoading.value   = true
  resultMsg.value     = ''
  banReason.value     = ''
  banDurationPreset.value = 'permanent'
  banDurationCustom.value = ''
  // 面板打开时预加载权限组列表
  emit('request-groups')
})

const canBanAll  = computed(() => !!props.email && props.allChars.length > 0)
const avatarBg   = computed(() => {
  const colors = ['#6366f1','#0ea5e9','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899']
  let h = 0; for (const c of (props.playerName || '')) h = (h * 31 + c.charCodeAt(0)) & 0xffff
  return colors[h % colors.length]
})

function showResult(ok, msg) {
  resultOk.value  = ok
  resultMsg.value = msg
  clearTimeout(resultTimer)
  resultTimer = setTimeout(() => { resultMsg.value = '' }, 5000)
}

function doAction(action, extra = {}) {
  emit('action', { action, player: props.playerName, ...extra })
}

function getBanPayload(defaultReason = '由管理员操作') {
  const durationMap = {
    permanent: '',
    h1: '0d60m0s',
    h12: '0d720m0s',
    d1: '1d0m0s',
    d3: '3d0m0s',
    d7: '7d0m0s',
    d30: '30d0m0s',
  }
  const duration = banDurationPreset.value === 'custom'
    ? (banDurationCustom.value || '').trim()
    : (durationMap[banDurationPreset.value] || '')
  return {
    reason: (banReason.value || '').trim() || defaultReason,
    duration,
  }
}

function confirmBanOrUnban() {
  if (props.isBanned) {
    doAction('unban', { ticket: props.banTicket > 0 ? props.banTicket : undefined })
  } else {
    doAction('ban', getBanPayload('由管理员操作'))
  }
  banConfirm.value = false
}

function doBanAll() {
  banAllConfirm.value = false
  emit('ban-all', { chars: props.allChars, email: props.email, ...getBanPayload('由管理员一键封禁') })
}

function doGiveItem() {
  const trimmed = giveItemQuery.value.trim()
  if (!trimmed) return
  const idNum = parseInt(trimmed)
  if (!isNaN(idNum) && idNum > 0) {
    doAction('give_item', { item_id: idNum, stack: giveItemStack.value || 1 })
  } else {
    doAction('give_item', { item_name: trimmed, stack: giveItemStack.value || 1 })
  }
}

function doUnbanAll() {
  unbanAllConfirm.value = false
  // 通过 action 事件传递（父组件 handlePapAction 自动处理）
  emit('action', { action: 'unban_all', player: '', chars: props.allChars })
}

function toggleSetGroup() {
  setGroupOpen.value = !setGroupOpen.value
  if (setGroupOpen.value && !availableGroups.value.length) {
    groupsLoading.value = true
    emit('request-groups')
  }
}

// 暴露给父组件：显示操作结果；设置权限组列表
defineExpose({
  showResult,
  setAvailableGroups: (list) => { availableGroups.value = list; groupsLoading.value = false },
})
</script>

<style scoped>
/* ── overlay / panel ───────────────────────── */
.pap-overlay {
  position: fixed; inset: 0; z-index: 1020;
  background: rgba(0,0,0,.5);
  display: flex; align-items: center; justify-content: center;
  padding: 16px;
}
.pap-panel {
  background: #fff; border-radius: 14px;
  width: min(480px, 100%); max-height: 90vh;
  display: flex; flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,.22);
  overflow: hidden;
}
.pap-fade-enter-active, .pap-fade-leave-active { transition: opacity .2s; }
.pap-fade-enter-from, .pap-fade-leave-to { opacity: 0; }
.pap-fade-enter-active .pap-panel,
.pap-fade-leave-active .pap-panel { transition: transform .2s; }
.pap-fade-enter-from .pap-panel { transform: translateY(16px); }

/* ── header ────────────────────────────────── */
.pap-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; background: #f8fafc; border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}
.pap-header-left { display: flex; align-items: center; gap: 12px; }
.pap-avatar {
  width: 40px; height: 40px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem; font-weight: 700; color: #fff; flex-shrink: 0;
}
.pap-title  { font-size: .96rem; font-weight: 700; color: #0f172a; }
.pap-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 3px; }
.pap-badge  { font-size: .7rem; font-weight: 600; padding: 1px 7px; border-radius: 20px; display: flex; align-items: center; gap: 4px; }
.badge-online  { background: #dcfce7; color: #15803d; }
.badge-offline { background: #f1f5f9; color: #64748b; }
.badge-group   { background: #ede9fe; color: #6d28d9; }
.badge-email   { background: #e0f2fe; color: #0369a1; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.pap-close {
  background: none; border: none; cursor: pointer; padding: 5px;
  border-radius: 7px; color: #64748b; display: flex; align-items: center;
}
.pap-close:hover { background: #f1f5f9; color: #0f172a; }

/* ── body ───────────────────────────────────── */
.pap-body { flex: 1; overflow-y: auto; padding: 16px 18px; display: flex; flex-direction: column; gap: 16px; }

.pap-section { display: flex; flex-direction: column; gap: 8px; }
.pap-section-title {
  font-size: .72rem; font-weight: 700; color: #94a3b8;
  letter-spacing: .06em; text-transform: uppercase;
  display: flex; align-items: center; gap: 6px;
}
.section-tip { font-size: .68rem; font-weight: 400; color: #cbd5e1; text-transform: none; letter-spacing: 0; }
.danger-title { color: #dc2626; }

.pap-section-danger { padding: 10px 12px; background: #fff5f5; border-radius: 8px; border: 1px solid #fecaca; }

.pap-ban-form {
  margin: 4px 0 8px;
  padding: 8px;
  border: 1px solid #fecaca;
  border-radius: 6px;
  background: #fff;
}
.pap-ban-form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

/* ── info grid ──────────────────────────────── */
.pap-info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; }
.pap-info-item { display: flex; flex-direction: column; gap: 2px; }
.info-label { font-size: .68rem; color: #94a3b8; }
.info-val   { font-size: .82rem; color: #0f172a; font-weight: 500; }

/* ── actions grid ───────────────────────────── */
.pap-actions-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.pap-action-group { display: flex; flex-direction: column; gap: 6px; }

.pap-action-btn {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  padding: 7px 12px; border-radius: 7px; font-size: .8rem; font-weight: 500;
  cursor: pointer; border: none; transition: all .15s; width: 100%;
}
.pap-action-btn:disabled { opacity: .45; cursor: not-allowed; }
.btn-primary-outline { background: #ede9fe; color: #6d28d9; border: 1px solid #ddd6fe; }
.btn-primary-outline:hover:not(:disabled) { background: #ddd6fe; }
.btn-neutral { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }
.btn-neutral:hover:not(:disabled) { background: #e2e8f0; }
.btn-warn { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
.btn-warn:hover:not(:disabled) { background: #ffedd5; }
.btn-danger { background: #fee2e2; color: #dc2626; border: 1px solid #fecaca; }
.btn-danger:hover:not(:disabled) { background: #fecaca; }
.btn-danger-outline { background: transparent; color: #dc2626; border: 1px dashed #fca5a5; }
.btn-danger-outline:hover:not(:disabled) { background: #fff5f5; }

/* ── inline form ────────────────────────────── */
.pap-inline-form {
  display: flex; gap: 6px; align-items: center; flex-wrap: wrap;
  padding: 6px 8px; background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0;
}
.pap-input {
  flex: 1; min-width: 80px; padding: 5px 8px; border-radius: 5px;
  border: 1px solid #e2e8f0; font-size: .8rem; color: #0f172a;
  background: #fff; outline: none;
}
.pap-input:focus { border-color: #6366f1; }
.pap-input-sm { max-width: 64px; }
.pap-confirm-btn {
  padding: 5px 12px; border-radius: 5px; font-size: .78rem; font-weight: 600;
  background: #6366f1; color: #fff; border: none; cursor: pointer; white-space: nowrap;
}
.pap-confirm-btn:disabled { opacity: .45; cursor: not-allowed; }
.pap-confirm-btn:hover:not(:disabled) { background: #4f46e5; }
.btn-danger-sm { background: #dc2626; }
.btn-danger-sm:hover:not(:disabled) { background: #b91c1c; }

/* ── danger row ─────────────────────────────── */
.pap-danger-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.pap-confirm-tip { font-size: .78rem; color: #7c3aed; }
.pap-confirm-tip.danger { color: #dc2626; }
.pap-cancel-btn {
  padding: 5px 10px; border-radius: 5px; font-size: .78rem;
  background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0; cursor: pointer;
}
.pap-cancel-btn:hover { background: #e2e8f0; }

/* ── stat form ──────────────────────────────── */
.pap-stat-form { display: flex; flex-direction: column; gap: 6px; }
.pap-stat-row { display: flex; align-items: center; gap: 10px; }
.pap-stat-row label { font-size: .8rem; color: #475569; width: 64px; flex-shrink: 0; }

/* ── result ─────────────────────────────────── */
.pap-result {
  display: flex; align-items: center; gap: 7px;
  padding: 9px 12px; border-radius: 7px; font-size: .82rem; font-weight: 500;
}
.result-ok  { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.result-err { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.pap-msg-enter-active, .pap-msg-leave-active { transition: opacity .2s, transform .2s; }
.pap-msg-enter-from, .pap-msg-leave-to { opacity: 0; transform: translateY(-4px); }

/* ── slide form ─────────────────────────────── */
.pap-slide-enter-active, .pap-slide-leave-active { transition: opacity .15s, max-height .2s; max-height: 80px; overflow: hidden; }
.pap-slide-enter-from, .pap-slide-leave-to { opacity: 0; max-height: 0; }
</style>
