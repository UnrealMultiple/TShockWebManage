<template>
  <div class="um-page">
    <!-- 页头 -->
    <div class="page-header">
      <h1 class="page-title">用户管理</h1>
      <button class="btn btn-sm btn-outline" @click="loadData" :disabled="loading">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/></svg>
        {{ loading ? '加载中…' : '刷新' }}
      </button>
    </div>

    <div class="um-body">

    <!-- 无服务器提示 -->
    <div v-if="!activeKey" class="empty-hint-box">
      <div class="empty-icon-wrap">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
      </div>
      <p>请先在左侧选择一个服务器</p>
    </div>

    <template v-else>

      <!-- ① 面板成员 -->
      <div class="section-card">
        <div class="section-header-row">
          <div class="section-card-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px;vertical-align:middle;margin-right:8px">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
            面板成员
          </div>
          <button class="btn btn-sm btn-outline" @click="loadData" :disabled="loading">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/></svg>
            {{ loading ? '加载中…' : '刷新' }}
          </button>
        </div>
        <div v-if="loading" class="loading-state">加载中…</div>
        <div v-else class="table-wrap">
          <table class="um-table">
            <thead>
              <tr>
                <th>账号</th>
                <th>面板权限</th>
                <th>加入时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in members" :key="m.user_id">
                <td>
                  <div class="user-cell">
                    <div class="avatar-sm" :style="{ background: avatarColor(m.email) }">
                      {{ m.email[0].toUpperCase() }}
                    </div>
                    <span class="user-email">{{ m.email }}</span>
                    <span v-if="m.user_id === serverOwnerId" class="badge-owner">Owner</span>
                  </div>
                </td>
                <td>
                  <span :class="['role-badge', 'role-' + m.role]">
                    {{ m.panel_group_name ?? panelGroupNameByRole(m.role) }}
                  </span>
                </td>
                <td class="muted-text">{{ formatTime(m.joined_at) }}</td>
                <td>
                  <button class="btn btn-sm btn-primary" @click="openDrawer(m)">管理</button>
                </td>
              </tr>
              <tr v-if="!members.length">
                <td colspan="4" class="empty-row">暂无成员数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ② 当前在线玩家 -->
      <div class="section-card">
        <div class="section-header-row">
          <div class="section-card-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px;vertical-align:middle;margin-right:8px">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
            当前在线玩家
            <span v-if="onlinePlayers.length" class="count-badge">{{ onlinePlayers.length }}</span>
          </div>
          <button class="btn btn-sm btn-outline" @click="refreshOnlinePlayers()" :disabled="onlineFetch.loading.value || !agentOnline">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/></svg>
            {{ onlineFetch.loading.value ? '查询中…' : '刷新' }}
          </button>
        </div>
        <div v-if="!agentOnline" class="agent-offline-tip">Agent 未连接，无法查询在线玩家</div>
        <div v-else-if="onlineFetch.loading.value" class="loading-state">查询在线玩家…</div>
        <div v-else-if="!onlinePlayers.length" class="empty-row-inline">当前没有玩家在线</div>
        <div v-else class="player-pill-cloud">
          <div v-for="p in onlinePlayers" :key="p.name" class="player-pill">
            <span class="online-dot dot-on"></span>
            <span class="pill-name">{{ p.name }}</span>
            <span v-if="p.group" class="pill-group">{{ p.group }}</span>
            <button class="pill-inv-btn" @click.stop="openPlayerPanel(p.name, { isOnline: true, group: p.group, email: p.panel_email })" title="更多操作">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:10px;height:10px"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>
            </button>
          </div>
        </div>
      </div>

      <!-- ③ 游戏内未绑定账号 -->
      <div class="section-card">
        <div class="section-header-row">
          <div class="section-card-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px;vertical-align:middle;margin-right:8px">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
              <line x1="12" y1="11" x2="12" y2="17"/>
              <line x1="9" y1="14" x2="15" y2="14"/>
            </svg>
            游戏内未绑定账号
            <span v-if="unboundTotal > 0" class="count-badge count-badge-muted">{{ unboundTotal }}</span>
          </div>
          <button class="btn btn-sm btn-outline" @click="refreshUnboundPlayers()" :disabled="allGameFetch.loading.value || !agentOnline">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/></svg>
            {{ allGameFetch.loading.value ? '查询中…' : '刷新' }}
          </button>
        </div>
        <div v-if="!agentOnline" class="agent-offline-tip">Agent 未连接，无法查询游戏账号</div>
        <div v-else-if="allGameFetch.loading.value" class="loading-state">查询中…</div>
        <template v-else>
          <div v-if="!pagedUnbound.length" class="empty-row-inline">暂无未绑定的游戏账号</div>
          <div v-else class="player-pill-cloud">
            <div v-for="u in pagedUnbound" :key="u.name" class="player-pill">
              <span :class="['online-dot', u.online ? 'dot-on' : 'dot-off']"></span>
              <span class="pill-name">{{ u.name }}</span>
              <span class="pill-group">{{ u.group || 'default' }}</span>
              <span v-if="u.online" class="pill-online-tag">在线</span>
              <button class="pill-inv-btn" @click.stop="openPlayerPanel(u.name, { isOnline: !!u.online, group: u.group })" title="更多操作">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:10px;height:10px"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>
              </button>
            </div>
          </div>
          <div class="pagination" v-if="unboundTotal > unboundPageSize">
            <button class="btn btn-xs btn-outline" :disabled="unboundPage <= 1" @click="unboundPage--">上一页</button>
            <span class="page-info">第 {{ unboundPage }} 页 / 共 {{ unboundTotalPages }} 页（{{ unboundTotal }} 条）</span>
            <button class="btn btn-xs btn-outline" :disabled="unboundPage >= unboundTotalPages" @click="unboundPage++">下一页</button>
          </div>
        </template>
      </div>

    </template>

    </div><!-- /um-body -->

    <!-- ═══ 详情抽屉 ═══ -->
    <transition name="drawer-fade">
      <div v-if="drawerOpen" class="drawer-overlay" @click.self="closeDrawer">
        <div class="drawer-panel" @click.stop>

          <!-- 抽屉头部 -->
          <div class="drawer-header">
            <button class="drawer-close" @click="closeDrawer" title="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:15px;height:15px"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
            <div class="drawer-user-info">
              <div class="avatar-lg" :style="{ background: avatarColor(drawerMember?.email || '') }">
                {{ (drawerMember?.email || '?')[0].toUpperCase() }}
              </div>
              <div class="drawer-user-meta">
                <div class="drawer-email">{{ drawerMember?.email }}</div>
                <div class="drawer-role-row">
                  <span class="label-sm">面板权限：</span>
                  <select
                    class="role-select"
                    v-model="drawerPanelGroupId"
                    :disabled="drawerMember?.user_id === serverOwnerId || !canManage"
                    @change="updatePanelGroup"
                  >
                    <option :value="null">— 未分配 —</option>
                    <option v-for="g in panelGroups" :key="g.id" :value="g.id">{{ g.name }}</option>
                  </select>
                  <span v-if="panelGroupUpdating" class="role-saving">保存中…</span>
                  <span v-if="panelGroupSaved" class="role-saved">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:13px;height:13px;vertical-align:middle"><polyline points="20 6 9 17 4 12"/></svg>
                    已保存
                  </span>
                  <button
                    v-if="drawerMember?.user_id !== serverOwnerId && isOwner"
                    class="btn btn-xs btn-danger kick-btn"
                    style="margin-left:auto"
                    @click="handleKickMember"
                  >踢出</button>
                </div>
              </div>
            </div>
          </div>

          <!-- 分割线 -->
          <div class="drawer-divider"></div>

          <!-- 游戏角色区 -->
          <div class="drawer-section-title">
            <span>游戏角色</span>
            <button class="btn btn-xs btn-outline" @click="loadMemberCharacters" :disabled="charsLoading">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:13px;height:13px;flex-shrink:0"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/></svg>
              {{ charsLoading ? '查询中…' : '刷新' }}
            </button>
          </div>

          <div v-if="charsLoading" class="players-loading">正在加载角色数据…</div>
          <div v-else-if="!memberChars.length" class="players-loading">该用户暂未注册任何游戏角色</div>

          <div v-else class="player-cards">
            <div v-for="p in memberChars" :key="p.character_name" class="player-card">
              <!-- 卡片头 -->
              <div class="pc-header">
                <div class="pc-name-row">
                  <span class="pc-name">{{ p.character_name }}</span>
                  <span :class="['online-dot', p.online ? 'dot-on' : 'dot-off']"></span>
                  <span class="pc-online-text">{{ p.online ? '在线' : '离线' }}</span>
                </div>
                <span class="pc-group">{{ p.group || '未知组' }}</span>
              </div>

              <!-- 操作按钮行 -->
              <div class="pc-actions">
                <template v-if="deleteCharConfirm[p.character_name]">
                  <span class="del-confirm-hint">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px;vertical-align:middle"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    确认删除？
                  </span>
                  <button class="btn btn-xs btn-danger"
                    :disabled="deleteCharLoading[p.character_name]"
                    @click="confirmDeleteChar(p.character_name)">
                    {{ deleteCharLoading[p.character_name] ? '删除中…' : '确认' }}
                  </button>
                  <button class="btn btn-xs btn-outline"
                    @click="deleteCharConfirm[p.character_name] = false">取消</button>
                </template>
                <button v-else
                  class="btn btn-xs btn-outline-danger"
                  :disabled="actionLoading[p.character_name]"
                  @click="deleteCharConfirm[p.character_name] = true"
                  title="删除游戏角色绑定及TShock账号"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
                  删除角色
                </button>
                <button class="btn btn-xs btn-outline" :disabled="!agentOnline"
                  style="margin-left:auto"
                  @click="openPlayerPanel(p.character_name, { isOnline: p.online, group: p.group, email: drawerMember?.email, allChars: memberChars.map(c => c.character_name) })"
                  title="查看详情与执行操作">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>
                  更多操作
                </button>
              </div>
            </div>
          </div>

          <!-- 下面是 drawer 底部游戏角色展示结束 -->

        </div>
      </div>
    </transition>

    <!-- ═══ 玩家操作面板 ═══ -->
    <PlayerActionPanel
      :show="papVisible"
      :player-name="papPlayer.name"
      :email="papPlayer.email"
      :group="papPlayer.group"
      :is-online="papPlayer.isOnline"
      :is-banned="papIsBanned"
      :ban-ticket="papBanTicket"
      :is-muted="papPlayer.isMuted"
      :hp="papPlayer.hp"
      :max-hp="papPlayer.maxHp"
      :mana="papPlayer.mana"
      :max-mana="papPlayer.maxMana"
      :agent-online="agentOnline"
      :ssc-enabled="papSscEnabled"
      :all-chars="papPlayer.allChars"
      ref="papRef"
      @close="papVisible = false"
      @open-inventory="name => { papVisible = false; openInventory(name) }"
      @action="handlePapAction"
      @ban-all="handlePapBanAll"
      @request-groups="handleRequestGroups"
    />

    <!-- ═══ 背包查看/编辑模态框 ═══ -->
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
      :can-edit="canManage && agentOnline && invSscEnabled"
      :saving="invSaving"
      @close="invVisible = false"
      @save="handleSaveInventory"
    />

  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, onUnmounted, watch } from 'vue'
import { getToken } from '@/api/auth'
import { deleteMemberCharacter, kickMember } from '@/api/servers'
import { apiUrl } from '@/api/base'
import { usePlayerList } from '@/composables/usePlayerList'
import InventoryModal from '@/components/InventoryModal.vue'
import PlayerActionPanel from '@/components/PlayerActionPanel.vue'

// ── 注入全局状态 ──────────────────────────────────────────────────
const myServers   = inject('myServers', ref([]))
const activeKey   = inject('activeServerKey', ref(''))
const activeServer = inject('activeServer', ref(null))

const props = defineProps({
  wsState:     { type: String, default: 'disconnected' },
  agentOnline: { type: Boolean, default: false },
})

// ── 权限判断 ──────────────────────────────────────────────────────
const canManage = computed(() => {
  const s = activeServer.value
  if (!s) return false
  const role = s.server_role
  if (role === 'owner' || role === 'web_staff') return true
  const g = s.panel_group_name
  return g === '服主' || g === '管理'
})
const isOwner = computed(() => {
  const s = activeServer.value
  if (!s) return false
  return s.server_role === 'owner' || s.panel_group_name === '服主'
})
const serverOwnerId = computed(() => activeServer.value?.owner_id ?? null)

// ── 在线玩家 / 未绑定账号 composable 实例 ─────────────────────────
const onlineFetch  = usePlayerList()   // ② 当前在线玩家区
const allGameFetch = usePlayerList()   // ③ 游戏内未绑定账号区
const charMap      = ref({})           // { character_name: email }

const onlinePlayers = computed(() =>
  onlineFetch.players.value
    .filter(pl => pl.online)
    .map(pl => ({ name: pl.name, group: pl.group || '', panel_email: charMap.value[pl.name] || null }))
)

const allUnboundUsers = computed(() => {
  const boundNames = new Set(Object.keys(charMap.value).map(n => n.toLowerCase()))
  return allGameFetch.players.value
    .filter(pl => {
      const name = (pl.name || '').trim()
      if (!name) return false
      return !boundNames.has(name.toLowerCase())
    })
    .sort((a, b) => {
      if (!!a.online !== !!b.online) return a.online ? -1 : 1
      return (a.name || '').localeCompare(b.name || '', 'zh-CN', { sensitivity: 'base' })
    })
})

const unboundPage      = ref(1)
const unboundPageSize  = 15
const unboundTotal      = computed(() => allUnboundUsers.value.length)
const unboundTotalPages = computed(() => Math.max(1, Math.ceil(unboundTotal.value / unboundPageSize)))
const pagedUnbound      = computed(() => {
  const start = (unboundPage.value - 1) * unboundPageSize
  return allUnboundUsers.value.slice(start, start + unboundPageSize)
})

async function loadCharMap() {
  if (!serverIdCache.value) return
  try {
    const res = await fetch(apiUrl(`/api/servers/${serverIdCache.value}/character-map`), {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (res.ok) charMap.value = await res.json()
  } catch { /* ignore */ }
}

// ── 成员列表 ──────────────────────────────────────────────────────
const members = ref([])
const loading = ref(false)

async function loadData() {
  if (!activeKey.value || !canManage.value) return
  // 找到当前服务器 id
  const srv = myServers.value.find(s => s.agent_key === activeKey.value)
  if (!srv) return
  loading.value = true
  try {
    const res = await fetch(apiUrl(`/api/servers/${srv.id}`), {
      headers: { Authorization: `Bearer ${getToken()}` }
    })
    if (!res.ok) throw new Error((await res.json()).detail || '请求失败')
    const data = await res.json()
    members.value = data.members || []
    serverIdCache.value = data.id
    // 加载 charMap、权限组列表，并触发 Agent 查询
    await Promise.all([loadCharMap(), loadPanelGroups()])
    if (props.agentOnline) {
      onlineFetch.request(activeKey.value)
      allGameFetch.request(activeKey.value)
    }
  } catch (e) {
    alert('加载成员失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

const serverIdCache = ref(null)

// ── 重新加载的 watch ─────────────────────────────────────────────
watch([activeKey, canManage], () => { loadData() }, { immediate: true })

// ── 抽屉状态 ──────────────────────────────────────────────────────
const drawerOpen   = ref(false)
const drawerMember = ref(null)

function openDrawer(m) {
  drawerMember.value = m
  drawerOpen.value   = true
  drawerPanelGroupId.value = null
  panelGroupSaved.value    = false
  // 打开抽屉时自动加载该用户的绑定角色
  memberChars.value = []
  charsLoading.value = false
  loadMemberCharacters()
  loadMemberPanelGroup()
}

function closeDrawer() {
  drawerOpen.value = false
  drawerMember.value = null
  setGroupTarget.value = null
  drawerPanelGroupId.value = null
}

// ── 面板权限组 ────────────────────────────────────────────────────
const panelGroups        = ref([])
const drawerPanelGroupId = ref(null)
const panelGroupUpdating = ref(false)
const panelGroupSaved    = ref(false)
let panelGroupSavedTimer = null

async function loadPanelGroups() {
  if (!serverIdCache.value) return
  try {
    const res = await fetch(apiUrl(`/api/servers/${serverIdCache.value}/panel-groups`), {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (res.ok) {
      const data = await res.json()
      panelGroups.value = data.data || []
    }
  } catch { /* ignore */ }
}

// role → 对应默认权限组 id
function roleToDefaultGroupId(role) {
  const nameMap = { owner: '服主', web_staff: '管理', member: '成员' }
  const groupName = nameMap[role]
  if (!groupName) return null
  return panelGroups.value.find(g => g.name === groupName)?.id ?? null
}

// 成员列表用：根据 role 显示对应权限组名
function panelGroupNameByRole(role) {
  const id = roleToDefaultGroupId(role)
  if (id) {
    const g = panelGroups.value.find(g => g.id === id)
    if (g) return g.name
  }
  return { owner: '服主', web_staff: '管理', member: '成员' }[role] ?? role
}

async function loadMemberPanelGroup() {
  if (!serverIdCache.value || !drawerMember.value) return
  try {
    const res = await fetch(
      apiUrl(`/api/servers/${serverIdCache.value}/members/${drawerMember.value.user_id}/panel-group`),
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
    if (res.ok) {
      const data = await res.json()
      if (data.data?.id) {
        drawerPanelGroupId.value = data.data.id
      } else {
        // 未分配时按 role 自动选中并写入对应默认权限组
        const defaultId = roleToDefaultGroupId(drawerMember.value.role)
        drawerPanelGroupId.value = defaultId
        if (defaultId) {
          // 静默写入 DB，使列表列与抽屉保持一致
          await fetch(
            apiUrl(`/api/servers/${serverIdCache.value}/members/${drawerMember.value.user_id}/panel-group`),
            {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
              body: JSON.stringify({ group_id: defaultId }),
            },
          )
          await loadData()
        }
      }
    }
  } catch { /* ignore */ }
}

async function handleKickMember() {
  if (!serverIdCache.value || !drawerMember.value) return
  if (!confirm(`确定踢出「${drawerMember.value.email}」吗？`)) return
  try {
    await kickMember(serverIdCache.value, drawerMember.value.user_id)
    closeDrawer()
    await loadData()
  } catch (e) {
    alert('踢出失败: ' + e.message)
  }
}

async function updatePanelGroup() {
  if (!serverIdCache.value || !drawerMember.value || drawerPanelGroupId.value === null) return
  panelGroupUpdating.value = true
  panelGroupSaved.value    = false
  try {
    const res = await fetch(
      apiUrl(`/api/servers/${serverIdCache.value}/members/${drawerMember.value.user_id}/panel-group`),
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ group_id: drawerPanelGroupId.value }),
      },
    )
    if (!res.ok) throw new Error((await res.json()).detail || '修改失败')
    panelGroupSaved.value = true
    // 同步刷新列表中该成员的 role 显示
    await loadData()
    clearTimeout(panelGroupSavedTimer)
    panelGroupSavedTimer = setTimeout(() => { panelGroupSaved.value = false }, 3000)
  } catch (e) {
    alert('修改面板权限失败: ' + e.message)
    await loadMemberPanelGroup()
  } finally {
    panelGroupUpdating.value = false
  }
}

// ── 游戏角色列表（来自 API，只显示该用户绑定的角色）────────────────
const memberChars  = ref([])
const charsLoading = ref(false)

async function loadMemberCharacters() {
  if (!serverIdCache.value || !drawerMember.value) return
  charsLoading.value = true
  memberChars.value = []
  try {
    const res = await fetch(
      apiUrl(`/api/servers/${serverIdCache.value}/members/${drawerMember.value.user_id}/characters`),
      { headers: { Authorization: `Bearer ${getToken()}` } }
    )
    if (!res.ok) throw new Error((await res.json()).detail || '请求失败')
    const data = await res.json()
    // 初始状态均为离线，若 Agent 在线则通过 player_list 补充在线状态
    memberChars.value = data.map(c => ({
      character_name: c.character_name,
      registered_at: c.registered_at,
      online: false,
      group: '',
    }))
    // 如 Agent 在线，发送 player_list 补充在线/组信息
    if (props.agentOnline && memberChars.value.length) {
      pendingPlayerReqId = Math.random().toString(36).slice(2)
      window.__tshockSend?.({
        type:    'player_list',
        msg_id:  pendingPlayerReqId,
        timestamp: Date.now(),
        payload: { agent_key: activeKey.value },
      })
    }
  } catch (e) {
    console.warn('[MemberChars] 加载失败:', e.message)
  } finally {
    charsLoading.value = false
  }
}

let pendingPlayerReqId = null

// ── 玩家操作 ──────────────────────────────────────────────────────
const actionLoading  = ref({})
const actionMsg      = ref({})
const actionMsgClass = ref({})

function playerAction(action, player) {
  const reqId = Math.random().toString(36).slice(2)
  actionLoading.value[player.character_name] = reqId
  actionMsg.value[player.character_name] = ''
  window.__tshockSend?.({
    type:      'player_action',
    msg_id:    reqId,
    timestamp: Date.now(),
    payload:   { agent_key: activeKey.value, action, player: player.character_name, reason: '由管理员操作' }
  })
}

// ── 删除游戏角色（管理员）───────────────────────────────────────────
const deleteCharConfirm = ref({})
const deleteCharLoading = ref({})

async function confirmDeleteChar(charName) {
  if (!serverIdCache.value || !drawerMember.value) return
  deleteCharLoading.value[charName] = true
  try {
    await deleteMemberCharacter(serverIdCache.value, drawerMember.value.user_id, charName)
    deleteCharConfirm.value[charName] = false
    await loadMemberCharacters()
  } catch (e) {
    alert('删除角色失败: ' + e.message)
    deleteCharConfirm.value[charName] = false
  } finally {
    deleteCharLoading.value[charName] = false
  }
}

// ── 修改游戏组 ────────────────────────────────────────────────────
const setGroupTarget = ref(null)
const newGroupName   = ref('')

function openSetGroup(p) {
  setGroupTarget.value = p
  newGroupName.value   = p.group || ''
}

function confirmSetGroup() {
  if (!setGroupTarget.value || !newGroupName.value.trim()) return
  const p = setGroupTarget.value
  const reqId = Math.random().toString(36).slice(2)
  actionLoading.value[p.character_name] = reqId
  actionMsg.value[p.character_name] = ''
  window.__tshockSend?.({
    type:      'player_action',
    msg_id:    reqId,
    timestamp: Date.now(),
    payload:   { agent_key: activeKey.value, action: 'setgroup', player: p.character_name, group: newGroupName.value.trim() }
  })
  setGroupTarget.value = null
}

// ── 玩家操作面板 ──────────────────────────────────────────────────
const papVisible   = ref(false)
const papSscEnabled = ref(false)
const papPlayer   = ref({ name: '', email: '', group: '', isOnline: false, isMuted: false, hp: 0, maxHp: 0, mana: 0, maxMana: 0, allChars: [] })
const papIsBanned = ref(false)
const papBanTicket = ref(0)
const papRef      = ref(null)
let   papReqId    = null
let   papBanReqId = null

function openPlayerPanel(name, opts = {}) {
  papPlayer.value = {
    name,
    email:    opts.email    || '',
    group:    opts.group    || '',
    isOnline: !!opts.isOnline,
    isMuted:  false,
    hp: 0, maxHp: 0, mana: 0, maxMana: 0,
    allChars: opts.allChars || [],
  }
  papSscEnabled.value = false
  papIsBanned.value = false
  papBanTicket.value = 0
  papVisible.value = true
  // 若在线，拉取背包数据填充 hp/mana/ssc 信息
  if (opts.isOnline && props.agentOnline) {
    papReqId = Math.random().toString(36).slice(2)
    window.__tshockSend?.({
      type: 'get_inventory', msg_id: papReqId, timestamp: Date.now(),
      payload: { agent_key: activeKey.value, username: name },
    })
  }
  if (props.agentOnline) {
    papBanReqId = Math.random().toString(36).slice(2)
    window.__tshockSend?.({
      type: 'player_action', msg_id: papBanReqId, timestamp: Date.now(),
      payload: { agent_key: activeKey.value, action: 'ban_status', player: name },
    })
  }
}

function handlePapAction(evt) {
  const reqId = Math.random().toString(36).slice(2)
  const reason = (evt?.reason || '').trim() || '由管理员操作'
  const duration = (evt?.duration || '').trim()
  window.__tshockSend?.({
    type: 'player_action', msg_id: reqId, timestamp: Date.now(),
    payload: { agent_key: activeKey.value, ...evt, reason, duration },
  })
  // 监听结果
  const handler = (e) => {
    const pkt = e.detail || {}
    if (pkt.type !== 'player_action_resp') return
    const p = pkt.payload || {}
    if (p.ref_id !== reqId) return
    window.removeEventListener('ws-message', handler)
    papRef.value?.showResult(!!p.success, p.msg || (p.success ? '操作成功' : '操作失败'))
    if (p.success) {
      loadMemberCharacters()
      onlineFetch.request(activeKey.value)
      allGameFetch.request(activeKey.value)
    }
  }
  window.addEventListener('ws-message', handler)
  setTimeout(() => window.removeEventListener('ws-message', handler), 15000)
}

function handlePapBanAll({ chars, reason, duration }) {
  const reqId = Math.random().toString(36).slice(2)
  const banReason = (reason || '').trim() || '由管理员一键封禁'
  const banDuration = (duration || '').trim()
  window.__tshockSend?.({
    type: 'player_action', msg_id: reqId, timestamp: Date.now(),
    payload: { agent_key: activeKey.value, action: 'ban_all', player: '', chars, reason: banReason, duration: banDuration },
  })
  const handler = (e) => {
    const pkt = e.detail || {}
    if (pkt.type !== 'player_action_resp') return
    const p = pkt.payload || {}
    if (p.ref_id !== reqId) return
    window.removeEventListener('ws-message', handler)
    papRef.value?.showResult(!!p.success, p.msg || '操作完成')
    if (p.success) loadMemberCharacters()
  }
  window.addEventListener('ws-message', handler)
  setTimeout(() => window.removeEventListener('ws-message', handler), 15000)
}

function refreshOnlinePlayers()  { onlineFetch.request(activeKey.value) }
function refreshUnboundPlayers() { allGameFetch.request(activeKey.value) }

function handleRequestGroups() {
  window.__tshockSend?.({ type: 'get_groups', msg_id: `gg-${Date.now()}`, timestamp: Date.now(),
    payload: { agent_key: activeKey.value } })
}

// ── 背包查看/编辑 ─────────────────────────────────────────────────
const invVisible    = ref(false)
const invUsername   = ref('')
const invLoading    = ref(false)
const invError      = ref('')
const invSlots      = ref([])
const invHealth     = ref(0)
const invMaxHealth  = ref(0)
const invMana       = ref(0)
const invMaxMana    = ref(0)
const invIsOnline    = ref(false)
const invSscEnabled  = ref(false)
const invSaving      = ref(false)
let pendingInvReqId     = null
let pendingSaveInvReqId = null
let invLoadingTimer     = null

function openInventory(charName) {
  if (!props.agentOnline) return
  invVisible.value  = true
  invUsername.value = charName
  invLoading.value  = true
  invError.value    = ''
  invSlots.value    = []
  clearTimeout(invLoadingTimer)
  pendingInvReqId = Math.random().toString(36).slice(2)
  window.__tshockSend?.({
    type:      'get_inventory',
    msg_id:    pendingInvReqId,
    timestamp: Date.now(),
    payload:   { agent_key: activeKey.value, username: charName },
  })
  invLoadingTimer = setTimeout(() => {
    if (invLoading.value) {
      invLoading.value = false
      invError.value   = '请求超时，请确认 Agent 在线且玩家账号存在角色数据'
      pendingInvReqId  = null
    }
  }, 10000)
}

function handleSaveInventory(savePayload) {
  invSaving.value = true
  const slotMap = savePayload?.slots ?? savePayload
  const slots = Object.values(slotMap).sort((a, b) => a.index - b.index)
  pendingSaveInvReqId = Math.random().toString(36).slice(2)
  const payload = {
    agent_key: activeKey.value,
    username: invUsername.value,
    slots,
  }
  if (typeof savePayload?.max_hp === 'number') payload.max_hp = savePayload.max_hp
  if (typeof savePayload?.max_mana === 'number') payload.max_mana = savePayload.max_mana
  window.__tshockSend?.({
    type:      'save_inventory',
    msg_id:    pendingSaveInvReqId,
    timestamp: Date.now(),
    payload,
  })
}

// ── 接收 WebSocket 消息 ───────────────────────────────────────────
function onWsMessage(e) {
  const pkt = e.detail
  if (!pkt) return

  if (pkt.type === 'player_list_resp') {
    // 在线玩家区（composable 消费）
    if (onlineFetch.consume(pkt)) return
    // 未绑定账号区（composable 消费）
    if (allGameFetch.consume(pkt)) return
    // 抽屉角色在线状态
    const p = pkt.payload || {}
    if (pendingPlayerReqId && p.ref_id === pendingPlayerReqId) {
      pendingPlayerReqId = null
      if (p.success && memberChars.value.length) {
        const onlineMap = {}
        for (const pl of (p.players || [])) {
          onlineMap[pl.name] = { online: !!pl.online, group: pl.group || '' }
        }
        memberChars.value = memberChars.value.map(c => ({
          ...c,
          online: onlineMap[c.character_name]?.online ?? false,
          group:  onlineMap[c.character_name]?.group  ?? c.group,
        }))
      }
    }
    return
  }

  if (pkt.type === 'player_action_resp') {
    const p = pkt.payload || {}
    if (papBanReqId && p.ref_id === papBanReqId && p.action === 'ban_status') {
      papBanReqId = null
      papIsBanned.value = !!p.banned
      papBanTicket.value = Number(p.ticket || 0)
      return
    }
    const name = Object.keys(actionLoading.value).find(k => actionLoading.value[k] === p.ref_id)
    if (!name) return
    delete actionLoading.value[name]
    actionMsg.value[name] = p.msg || (p.success ? '操作成功' : '操作失败')
    actionMsgClass.value[name] = p.success ? 'msg-ok' : 'msg-err'
    if (p.success) loadMemberCharacters()
    setTimeout(() => { actionMsg.value[name] = '' }, 4000)
    return
  }

  if (pkt.type === 'get_inventory_resp') {
    const p = pkt.payload || {}
    // PlayerActionPanel 的 hp/mana/ssc 填充
    if (papReqId && p.ref_id === papReqId) {
      papReqId = null
      if (p.success) {
        papPlayer.value = { ...papPlayer.value, hp: p.health || 0, maxHp: p.max_health || 0, mana: p.mana || 0, maxMana: p.max_mana || 0 }
        papSscEnabled.value = !!p.ssc_enabled
      }
    }
    if (p.ref_id !== pendingInvReqId) return
    pendingInvReqId = null
    invLoading.value = false
    if (p.success) {
      invSlots.value      = p.slots       || []
      invHealth.value     = p.health      || 0
      invMaxHealth.value  = p.max_health  || 0
      invMana.value       = p.mana        || 0
      invMaxMana.value    = p.max_mana    || 0
      invIsOnline.value   = !!p.is_online
      invSscEnabled.value = !!p.ssc_enabled
    } else {
      invError.value = p.msg || '加载背包数据失败'
    }
    return
  }

  if (pkt.type === 'save_inventory_resp') {
    const p = pkt.payload || {}
    if (p.ref_id !== pendingSaveInvReqId) return
    pendingSaveInvReqId = null
    invSaving.value = false
    alert(p.success ? (p.msg || '保存成功') : ('保存失败: ' + (p.msg || '未知错误')))
    return
  }

  if (pkt.type === 'get_groups_resp') {
    const p = pkt.payload || {}
    papRef.value?.setAvailableGroups(p.groups || [])
  }
}

onMounted(() => {
  window.addEventListener('ws-message', onWsMessage)
})
onUnmounted(() => {
  window.removeEventListener('ws-message', onWsMessage)
  clearTimeout(panelGroupSavedTimer)
  clearTimeout(invLoadingTimer)
  onlineFetch.reset()
  allGameFetch.reset()
})

// ── 工具函数 ──────────────────────────────────────────────────────
const COLORS = ['#6c63ff','#e44c65','#f5a623','#4caf89','#2196f3','#9c27b0','#ff5722']
function avatarColor(email) {
  let h = 0
  for (const c of email) h = (h * 31 + c.charCodeAt(0)) & 0xffff
  return COLORS[h % COLORS.length]
}

function formatTime(ts) {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleDateString('zh-CN')
}
</script>

<style scoped>
/* ── 页面布局 ────────────────────────────────────────── */
.um-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: #f8fafc;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 28px 16px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 12px;
}

.page-title {
  font-size: 1.35rem;
  font-weight: 700;
  margin: 0;
  color: #0f172a;
}

.um-body { flex: 1; overflow-y: auto; padding: 24px 28px; box-sizing: border-box; }

.empty-hint-box {
  text-align: center;
  padding: 60px 20px;
  color: #64748b;
}
.empty-hint-box .empty-icon { font-size: 2.5rem; margin-bottom: 12px; }
.empty-icon-wrap {
  display: flex; align-items: center; justify-content: center;
  width: 64px; height: 64px; margin: 0 auto 14px;
  background: #f1f5f9; border-radius: 16px;
}
.empty-icon-wrap svg { width: 32px; height: 32px; stroke: #94a3b8; }

.loading-state {
  text-align: center;
  padding: 40px;
  color: #64748b;
}

/* ── 表格 ────────────────────────────────────────────── */
.table-wrap {
  overflow-x: auto;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.um-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  font-size: .9rem;
}

.um-table th {
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  color: #64748b;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.um-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  color: #0f172a;
  vertical-align: middle;
}

.um-table tbody tr:last-child td { border-bottom: none; }
.um-table tbody tr:hover td { background: #f8fafc; }

.empty-row {
  text-align: center;
  padding: 40px !important;
  color: #94a3b8;
}

.muted-text { color: #94a3b8; font-size: .82rem; }

/* ── 用户单元格 ───────────────────────────────────────── */
.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar-sm {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: .85rem;
  color: #fff;
  flex-shrink: 0;
}

.user-email { font-size: .88rem; }

.badge-owner {
  background: linear-gradient(135deg, #f5a623, #e44c65);
  color: #fff;
  font-size: .7rem;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 20px;
}

/* ── 角色徽章 ────────────────────────────────────────── */
.role-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: .78rem;
  font-weight: 600;
}
.role-owner   { background: rgba(245,166,35,.15); color: #f5a623; }
.role-web_staff { background: rgba(108,99,255,.18); color: #a48bff; }
.role-member  { background: rgba(100,116,139,.1); color: #64748b; }

/* ── 按钮 ────────────────────────────────────────────── */
.btn {
  display: inline-flex; align-items: center; gap: 6px;
  border: none;
  border-radius: 7px;
  cursor: pointer;
  font-size: .82rem;
  font-weight: 500;
  padding: 6px 14px;
  transition: opacity .15s, transform .1s;
}
.btn:hover:not(:disabled) { opacity: .88; transform: translateY(-1px); }
.btn:disabled { opacity: .45; cursor: not-allowed; }

.btn-primary  { background: #6c63ff; color: #fff; }
.btn-outline  { background: transparent; border: 1px solid #d1d5db; color: #374151; }
.btn-warn     { background: rgba(245,166,35,.18); color: #f5a623; border: 1px solid rgba(245,166,35,.3); }
.btn-danger   { background: rgba(228,76,101,.18); color: #e44c65; border: 1px solid rgba(228,76,101,.3); }
.btn-disabled { background: rgba(100,116,139,.12); color: #4a5568; border: 1px solid rgba(100,116,139,.2); cursor: not-allowed; font-style: italic; }
.btn-outline-danger { background: transparent; border: 1px solid #fca5a5; color: #dc2626; }
.btn-outline-danger:hover:not(:disabled) { background: #fef2f2; }

.del-confirm-hint { font-size: .76rem; color: #b91c1c; font-weight: 500; }

.btn-sm { padding: 5px 12px; font-size: .8rem; }
.btn-xs { padding: 3px 9px; font-size: .76rem; border-radius: 5px; }

/* ── 新增区块通用 ──────────────────────────────────────── */
.section-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 18px 22px;
  margin-bottom: 20px;
}

.section-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.section-card-title {
  font-size: .9rem;
  font-weight: 700;
  color: #0f172a;
}

.members-header-row {
  margin-bottom: 8px;
}

.agent-offline-tip {
  font-size: .84rem;
  color: #94a3b8;
  padding: 8px 0;
}

.empty-row-inline {
  font-size: .84rem;
  color: #94a3b8;
  padding: 12px 0;
  text-align: center;
}

/* ── 在线玩家列表 ───────────────────────────────────────── */
.online-players-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.online-player-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: .88rem;
}

.op-name  { font-weight: 600; color: #0f172a; }
.op-sep   { color: #cbd5e1; }
.op-group-badge {
  background: rgba(108,99,255,.1);
  color: #6c63ff;
  font-size: .72rem;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 20px;
}
.op-panel-email {
  display: inline-flex; align-items: center; gap: 3px;
  color: #0284c7; font-size: .84rem;
}
.op-panel-email svg { width: 12px; height: 12px; stroke: currentColor; }
.op-unbound-tag { color: #94a3b8; font-size: .82rem; font-style: italic; }

/* ── 分页 ──────────────────────────────────────────────── */
.pagination {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  justify-content: flex-end;
}
.page-info { font-size: .82rem; color: #64748b; }

/* ── 抽屉 ────────────────────────────────────────────── */
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.55);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

.drawer-panel {
  width: min(480px, 96vw);
  height: 100%;
  background: #fff;
  border-left: 1px solid #e2e8f0;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.drawer-fade-enter-active,
.drawer-fade-leave-active { transition: opacity .25s; }
.drawer-fade-enter-active .drawer-panel,
.drawer-fade-leave-active .drawer-panel { transition: transform .25s ease; }
.drawer-fade-enter-from { opacity: 0; }
.drawer-fade-enter-from .drawer-panel { transform: translateX(60px); }
.drawer-fade-leave-to { opacity: 0; }
.drawer-fade-leave-to .drawer-panel { transform: translateX(60px); }

.drawer-close {
  align-self: flex-end;
  background: none;
  border: none;
  color: #64748b;
  font-size: 1.1rem;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  margin-bottom: 8px;
}
.drawer-close:hover { background: #f1f5f9; }

.drawer-user-info {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 4px;
}

.avatar-lg {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}

.drawer-user-meta { flex: 1; min-width: 0; }

.drawer-email {
  font-size: 1rem;
  font-weight: 600;
  color: #0f172a;
  word-break: break-all;
  margin-bottom: 10px;
}

.drawer-role-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.label-sm {
  font-size: .8rem;
  color: #64748b;
}

.role-select {
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  color: #0f172a;
  padding: 4px 10px;
  font-size: .82rem;
  cursor: pointer;
}
.role-select:disabled { opacity: .5; cursor: not-allowed; }

.role-saving { font-size: .78rem; color: var(--text-muted, #94a3b8); }
.role-saved  { font-size: .78rem; color: #4caf89; }

.drawer-divider {
  height: 1px;
  background: #e2e8f0;
  margin: 16px 0;
}
.drawer-danger-zone {
  padding: 0 0 8px;
}
.drawer-danger-zone .drawer-divider {
  background: #fecaca;
  margin-bottom: 12px;
}

/* ── 游戏角色区 ──────────────────────────────────────── */
.drawer-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: .9rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: .06em;
  margin-bottom: 12px;
}

.players-loading {
  text-align: center;
  padding: 24px;
  color: #94a3b8;
  font-size: .85rem;
}
.players-loading.warn { color: #f5a623; }

.player-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.player-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.pc-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pc-name {
  font-weight: 600;
  font-size: .92rem;
  color: #0f172a;
}

.online-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-on  { background: #4caf89; box-shadow: 0 0 5px #4caf89; }
.dot-off { background: #64748b; }

.pc-online-text { font-size: .75rem; color: #94a3b8; }

.pc-group {
  font-size: .78rem;
  padding: 2px 9px;
  border-radius: 20px;
  background: rgba(108,99,255,.1);
  color: #6c63ff;
}

.pc-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  flex-wrap: wrap;
}

.action-spin { font-size: .78rem; color: #94a3b8; }
.action-msg  { font-size: .78rem; }
.msg-ok  { color: #4caf89; }
.msg-err { color: #e44c65; }

/* ── 修改组面板 ──────────────────────────────────────── */
.setgroup-panel {
  margin-top: 16px;
  padding: 16px;
  border-radius: 10px;
  background: #f5f3ff;
  border: 1px solid rgba(108,99,255,.3);
}

.setgroup-title {
  font-size: .88rem;
  font-weight: 600;
  margin-bottom: 10px;
  color: #1e1b4b;
}

.setgroup-row {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.group-input {
  flex: 1;
  min-width: 120px;
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 7px;
  color: #0f172a;
  padding: 6px 10px;
  font-size: .85rem;
}
.group-input:focus {
  outline: none;
  border-color: #6c63ff;
}

/* ── 背包入口小按钮 ──────────────────────────────────────────────── */
.inv-tiny-btn {
  gap: 4px;
  font-size: .72rem;
  padding: 2px 8px;
}
.inv-tiny-btn svg { flex-shrink: 0; }

/* ── 数量徽章 ───────────────────────────────────────────────────── */
.count-badge {
  display: inline-flex; align-items: center; justify-content: center;
  background: rgba(108,99,255,.15); color: #6c63ff;
  font-size: .7rem; font-weight: 700; min-width: 20px; height: 18px;
  padding: 0 5px; border-radius: 20px; margin-left: 6px;
}
.count-badge-muted {
  background: rgba(100,116,139,.12); color: #64748b;
}

/* ── 在线小标签 ──────────────────────────────────────────────────── */
.online-badge-xs {
  background: #dcfce7; color: #15803d;
  font-size: .66rem; font-weight: 600; padding: 1px 6px; border-radius: 20px;
}

/* ── pill 流式布局 ──────────────────────────────────────────────── */
.player-pill-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-height: 220px;
  overflow-y: auto;
  padding: 2px 1px;
}
.player-pill-cloud::-webkit-scrollbar { width: 4px; height: 4px; }
.player-pill-cloud::-webkit-scrollbar-track { background: transparent; }
.player-pill-cloud::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 4px; }

.player-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: #f1f5f9;
  border: 1.5px solid #e2e8f0;
  border-radius: 999px;
  padding: 4px 8px 4px 6px;
  font-size: .82rem;
  transition: border-color .12s, background .12s;
  max-width: 240px;
}
.player-pill:hover { border-color: #c7d2fe; background: #f5f3ff; }
.player-pill.pill-offline:hover { border-color: #d1d5db; background: #f1f5f9; }

.pill-name {
  font-weight: 600;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}
.pill-group {
  background: rgba(108,99,255,.12);
  color: #6c63ff;
  font-size: .68rem;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 20px;
  white-space: nowrap;
}
.pill-email {
  display: inline-flex; align-items: center; color: #0284c7; flex-shrink: 0;
}
.pill-inv-btn {
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent; border: 1px solid #d1d5db;
  border-radius: 50%; width: 18px; height: 18px; padding: 0;
  cursor: pointer; color: #64748b; flex-shrink: 0;
  transition: background .12s, border-color .12s, color .12s;
}
.pill-inv-btn:hover { background: #6c63ff; border-color: #6c63ff; color: #fff; }
.pill-online-tag {
  font-size: .62rem; font-weight: 600; color: #15803d;
  background: #dcfce7; border-radius: 20px; padding: 1px 5px; white-space: nowrap;
}
</style>
