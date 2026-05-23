<template>
  <div class="dashboard">
    <!-- 欢迎横幅 -->
    <div class="welcome-banner">
      <div class="welcome-text">
        <h1>欢迎回来</h1>
        <p>{{ email }} · TShock 管理平台</p>
      </div>
      <div class="server-badge" :class="agentOnline ? 'online' : 'offline'">
        <span class="dot"></span>
        {{ agentOnline ? 'TShock 已连接' : 'TShock 未连接' }}
      </div>
    </div>

    <!-- 无服务器引导卡片 -->
    <div v-if="!hasServers" class="onboarding-card">
      <div class="oc-icon">🚀</div>
      <div class="oc-body">
        <h3>尚未绑定任何服务器</h3>
        <p>将 TShock Agent 插件安装到服务器并启动，将控制台显示的 Agent Key 填入绑定表单，就可开始全功能管理。</p>
        <router-link to="/servers" class="btn-goto">前往绑定 →</router-link>
      </div>
    </div>

    <!-- 是否显示状态卡片 -->
    <div class="card-grid">
      <div class="stat-card" v-for="card in statCards" :key="card.label">
        <div class="stat-icon" :style="{ background: card.bg }">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" v-html="card.icon" />
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </div>
      </div>
    </div>

    <!-- 服务器控制 -->
    <div v-if="canShowServerControl" class="ctrl-panel">
      <div class="ctrl-left">
        <div class="ctrl-label">服务器控制</div>
        <div class="ctrl-name">{{ activeServer?.name || '未选择服务器' }}</div>
        <div :class="['ctrl-badge', agentOnline ? 'badge-on' : 'badge-off']">
          <span class="ctrl-dot"></span>
          {{ agentOnline ? '运行中' : '已停止' }}
        </div>
      </div>
      <div class="ctrl-right">
        <template v-if="agentOnline">
          <template v-if="!confirmStop">
            <button
              class="power-btn btn-stop"
              :disabled="!canManageActiveServer || stopping"
              :title="canManageActiveServer ? '' : '需要管理权限'"
              @click="confirmStop = true"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18.36 6.64a9 9 0 1 1-12.73 0"/>
                <line x1="12" y1="2" x2="12" y2="12"/>
              </svg>
              {{ stopping ? '停止中…' : '停止服务器' }}
            </button>
            <button
              class="power-btn btn-restart"
              :disabled="!canManageActiveServer || restarting || stopping"
              :title="canManageActiveServer ? '' : '需要管理权限'"
              @click="doRestartServer"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"/>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
              </svg>
              {{ restarting ? '重启中…' : '重启服务器' }}
            </button>
            <span v-if="!canManageActiveServer" class="ctrl-hint">需要管理权限</span>
          </template>
          <template v-else>
            <span class="confirm-text">选择停止方式：</span>
            <button class="power-btn btn-stop-normal" @click="doStopServer('stop')">正常关闭</button>
            <button class="power-btn btn-stop-nosave" @click="doStopServer('stop_nosave')">不保存关闭</button>
            <button class="power-btn btn-cancel" @click="confirmStop = false">取消</button>
          </template>
        </template>
        <div v-else class="offline-hint">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <span>服务器已停止，请在主机端手动重启</span>
        </div>
      </div>
    </div>

    <!-- ── 资源监控 (服主专区) ────────────────────────────────────── -->
    <template v-if="isServerOwner && agentOnline">
      <div class="section-title">系统资源</div>
      <div v-if="serverStats?.resources" class="resource-grid">
        <div class="resource-card">
          <div class="rc-top">
            <span class="rc-label">CPU 占用</span>
            <span class="rc-value" :style="{ color: cpuColor }">{{ serverStats.resources.cpu_percent?.toFixed(1) }}%</span>
          </div>
          <div class="rc-bar-wrap">
            <div class="rc-bar" :style="{ width: Math.min(100, serverStats.resources.cpu_percent) + '%', background: cpuColor }"></div>
          </div>
        </div>
        <div class="resource-card">
          <div class="rc-top">
            <span class="rc-label">内存占用 (进程)</span>
            <span class="rc-value" style="color:#6366f1">{{ serverStats.resources.mem_mb }} MB</span>
          </div>
          <div class="rc-bar-wrap">
            <div class="rc-bar" :style="{ width: Math.min(100, serverStats.resources.mem_mb / 40.96) + '%', background: '#6366f1' }"></div>
          </div>
        </div>
        <div class="resource-card" v-if="serverStats.resources.net_send_kbps != null">
          <div class="rc-top">
            <span class="rc-label">网络流量</span>
            <span class="rc-value" style="color:#0ea5e9; font-size:15px">
              ↑{{ serverStats.resources.net_send_kbps?.toFixed(1) }}&nbsp;↓{{ serverStats.resources.net_recv_kbps?.toFixed(1) }} KB/s
            </span>
          </div>
          <div class="rc-bar-wrap">
            <div class="rc-bar" style="background:#0ea5e9"
              :style="{ width: Math.min(100, (serverStats.resources.net_send_kbps + serverStats.resources.net_recv_kbps) / 10.24) + '%' }">
            </div>
          </div>
        </div>
      </div>
      <div v-else class="empty-hint">暂无资源数据</div>
    </template>

    <!-- ── 在线玩家 ──────────────────────────────────────────────── -->
    <template v-if="agentOnline">
      <div class="section-title">
        在线玩家
        <span v-if="serverStats" class="section-badge">{{ serverStats.online_players }}/{{ serverStats.max_players }}</span>
      </div>
      <div v-if="serverStats?.players?.length" class="player-list">
        <div class="player-card"
          v-for="p in serverStats.players" :key="p.name"
          :class="{ 'player-card-sel': selectedPlayer === p.name }"
          @click="canManageActiveServer && toggleSelectPlayer(p.name)"
          :style="(canManageActiveServer || canViewOthersInventory) ? 'cursor:pointer' : ''"
        >
          <div class="pc-name-row">
            <div class="pc-name">{{ p.name }}</div>
            <button v-if="canManageActiveServer" class="pc-more-btn"
              @click.stop="openPlayerPanel(p)"
              title="玩家操作">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>
            </button>
            <button v-else-if="canViewOthersInventory" class="pc-more-btn"
              @click.stop="openInventory(p.name)"
              title="查看背包">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
          <div class="pc-bars">
            <div class="pc-bar-row">
              <span class="pc-bar-icon hp">❤</span>
              <div class="pc-bar-track">
                <div class="pc-bar-fill hp" :style="{ width: p.max_hp > 0 ? Math.round(p.hp/p.max_hp*100)+'%' : '0%' }"></div>
              </div>
              <span class="pc-bar-txt">{{ p.hp }}/{{ p.max_hp }}</span>
            </div>
            <div class="pc-bar-row">
              <span class="pc-bar-icon mp">✦</span>
              <div class="pc-bar-track">
                <div class="pc-bar-fill mp" :style="{ width: p.max_mana > 0 ? Math.round(p.mana/p.max_mana*100)+'%' : '0%' }"></div>
              </div>
              <span class="pc-bar-txt">{{ p.mana }}/{{ p.max_mana }}</span>
            </div>
          </div>
          <div class="pc-pos" v-if="canManageActiveServer">({{ p.tile_x }}, {{ p.tile_y }})</div>
        </div>
      </div>
      <div v-else-if="serverStats" class="empty-hint">暂无玩家在线</div>

      <!-- 玩家位置小地图 (仅服主可见) -->
      <div v-if="canManageActiveServer && agentOnline" class="minimap-wrap">
        <div class="minimap-header">
          <span class="minimap-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="mm-title-icon">
              <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
              <line x1="8" y1="2" x2="8" y2="18"/>
              <line x1="16" y1="6" x2="16" y2="22"/>
            </svg>
            玩家小地图
          </span>
          <div class="minimap-header-right">
            <span v-if="loadingDashMap" class="minimap-loading-txt">⏳ 生成中…</span>
            <template v-else>
              <div v-if="dashMapImg" class="minimap-zoom-btns">
                <button class="mz-btn" @click="mapZoom = Math.min(mapZoom * 1.25, 10)" title="放大">＋</button>
                <span class="mz-label">{{ Math.round(mapZoom * 100) }}%</span>
                <button class="mz-btn" @click="mapZoom = Math.max(mapZoom / 1.25, 0.5)" title="缩小">－</button>
                <button class="mz-btn mz-reset" @click="resetMapView" title="复位">⊡</button>
              </div>
              <button class="minimap-gen-btn" @click="fetchDashMap" :disabled="!activeServerKey">
                {{ dashMapImg ? '重新生成' : '生成地图' }}
              </button>
            </template>
          </div>
        </div>
        <div class="minimap-body">
          <div class="minimap-viewport" ref="minimapViewport"
            @wheel.prevent="onMapWheel"
            @mousedown.prevent="onMapMouseDown"
            @mousemove="onMapMouseMove"
            @mouseup="onMapMouseUp"
            @mouseleave="onMapMouseUp"
            @touchstart.prevent="onMapTouchStart"
            @touchmove="onMapTouchMove"
            @touchend="onMapTouchEnd"
            @click="onViewportClick"
            :style="{ cursor: mapDragging ? 'grabbing' : (dashMapImg ? 'grab' : 'default'), touchAction: 'none' }">
            <canvas ref="minimapCanvas" class="minimap-canvas"
              :style="{ transformOrigin: '0 0', transform: `translate(${mapPanX}px, ${mapPanY}px) scale(${mapZoom})` }">
            </canvas>
            <div v-if="!dashMapImg" class="minimap-placeholder">
              <span>{{ serverStats?.players?.length ? '有玩家在线，点击右上角"生成地图"查看位置' : '点击右上角"生成地图"获取世界地形' }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ── 世界进度 + 排行榜 ─────────────────────────────────────── -->
    <template v-if="agentOnline">
      <div class="bottom-grid">
        <!-- 世界进度 -->
        <div class="bottom-card">
          <div class="bc-head">
            <span class="bc-title">世界当前进度</span>
            <button class="bc-refresh" @click="fetchWorldProgress" title="刷新">↻</button>
          </div>
          <div v-if="worldProgress">
            <div :class="['world-mode-tag', !worldProgress.is_hardmode && 'normal']">
              {{ worldProgress.is_hardmode ? '肉后' : '肉前' }}
              · {{ worldProgress.is_crimson ? '猩红' : '腐化' }}
              · {{ worldDifficultyLabel }}
            </div>
            <div v-if="Number.isFinite(worldProgress.progress_percent)" class="world-progress-summary">
              当前进度：{{ worldProgress.progress_done }}/{{ worldProgress.progress_total }}
              （{{ worldProgress.progress_percent }}%）
            </div>
            <div class="boss-list">
              <div v-for="b in bossProgressList" :key="b.key" class="boss-item" :class="b.done ? 'done' : ''">
                <img class="boss-icon" :src="bossIconUrl(b)" :alt="b.label" loading="lazy" @error="onBossIconError" />
                <span class="boss-check">{{ b.done ? '☑' : '☐' }}</span>
                <span class="boss-name">{{ b.label }}</span>
              </div>
            </div>
          </div>
          <div v-else class="empty-hint">
            <button class="bc-load-btn" @click="fetchWorldProgress">加载进度</button>
          </div>
        </div>

        <!-- 排行榜 -->
        <div class="bottom-card">
          <div class="bc-head">
            <span class="bc-title">统计信息</span>
            <div class="lb-tabs">
              <button :class="['lb-tab', leaderboardTab==='time' && 'active']" @click="leaderboardTab='time'">在线时长</button>
              <button :class="['lb-tab', leaderboardTab==='deaths' && 'active']" @click="leaderboardTab='deaths'">死亡次数</button>
            </div>
            <button class="bc-refresh" @click="fetchPlayerStats" title="刷新">↻</button>
          </div>
          <div v-if="playerStats?.length" class="lb-list">
            <div v-for="(row, idx) in (leaderboardTab==='time' ? sortedByTime : sortedByDeaths)" :key="row.name" class="lb-row">
              <span class="lb-rank" :class="idx < 3 ? 'top'+idx : ''">{{ idx+1 }}</span>
              <span class="lb-name">{{ row.name }}</span>
              <span class="lb-val">{{ leaderboardTab==='time' ? fmtTime(row.online_seconds) : row.deaths + ' 次' }}</span>
            </div>
          </div>
          <div v-else class="empty-hint">
            <button class="bc-load-btn" @click="fetchPlayerStats">加载排行</button>
          </div>
        </div>
      </div>
    </template>

    <!-- ── 玩家操作面板 ── -->
    <PlayerActionPanel
      :show="papVisible"
      :player-name="papPlayer.name"
      :email="papPlayer.email"
      :group="papPlayer.group"
      :is-online="true"
      :is-banned="papIsBanned"
      :ban-ticket="papBanTicket"
      :hp="papPlayer.hp"
      :max-hp="papPlayer.maxHp"
      :mana="papPlayer.mana"
      :max-mana="papPlayer.maxMana"
      :agent-online="agentOnline"
      :ssc-enabled="papSscEnabled"
      :all-chars="papPlayer.allChars"
      :allow-assign-owner="canManageActiveServer"
      :current-owner-user-id="papPlayer.ownerUserId"
      :assign-owner-options="papAssignOwnerOptions"
      :allow-delete-account="canManageActiveServer"
      ref="papRef"
      @close="papVisible = false"
      @open-inventory="name => { papVisible = false; openInventory(name) }"
      @action="handlePapAction"
      @ban-all="handlePapBanAll"
      @request-groups="handleRequestGroups"
      @assign-owner="handlePapAssignOwner"
      @delete-account="handlePapDeleteAccount"
    />
    <!-- 背包模态框（Dashboard 全页用） -->
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
      :can-edit="canManageActiveServer && invSscEnabled"
      :saving="invSaving"
      @close="invVisible = false"
      @save="onSaveInventory"
    />

  </div>
</template>

<script setup>
import { computed, inject, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { getEmail, getToken } from '@/api/auth'
import {
  updateServer,
  deleteGameAccount,
  assignCharacterOwner,
  deleteMemberCharacter,
} from '@/api/servers'
import { apiUrl } from '@/api/base'
import PlayerActionPanel from '@/components/PlayerActionPanel.vue'
import InventoryModal from '@/components/InventoryModal.vue'
import { useInventory } from '@/composables/useInventory'

const myServers             = inject('myServers',             ref([]))
const activeServer          = inject('activeServer',          ref(null))
const canManageActiveServer = inject('canManageActiveServer', computed(() => false))
const hasPerm               = inject('hasPerm',               (() => false))
const isServerOwner         = inject('isServerOwner',         computed(() => false))
const activeServerKey       = inject('activeServerKey',       ref(''))
const hasServers            = computed(() => myServers.value.length > 0)
const canViewOthersInventory = computed(() => hasPerm('panel.inventory.view.others'))
const canShowServerControl = computed(() => hasServers.value && canManageActiveServer.value)

const props = defineProps({
  wsState:     { type: String,  default: 'disconnected' },
  agentOnline: { type: Boolean, default: false },
})

const email = getEmail() || ''

// ── 服务器控制 ────────────────────────────────────────────────
const confirmStop  = ref(false)
const stopping     = ref(false)
const restarting   = ref(false)

function sendWs(data) { window.__tshockSend?.(data) }

function fetchStatus() {
  if (!activeServerKey.value) return
  sendWs({ type: 'get_status', msg_id: Date.now().toString(), timestamp: Date.now(),
           payload: { agent_key: activeServerKey.value } })
}

function doStopServer(mode) {
  if (!canManageActiveServer.value || !activeServerKey.value) return
  stopping.value    = true
  confirmStop.value = false
  sendWs({ type: 'server_ctrl', msg_id: Date.now().toString(), timestamp: Date.now(),
           payload: { agent_key: activeServerKey.value, action: mode } })
}

function doRestartServer() {
  if (!canManageActiveServer.value || !activeServerKey.value) return
  restarting.value = true
  sendWs({ type: 'server_ctrl', msg_id: Date.now().toString(), timestamp: Date.now(),
           payload: { agent_key: activeServerKey.value, action: 'restart' } })
}

// ── 实时状态 ─────────────────────────────────────────────────
const serverStats    = ref(null)   // 增强 status payload
const worldProgress  = ref(null)   // 首领通关进度
const playerStats    = ref(null)   // 死亡/在线时长列表
const leaderboardTab = ref('time')
let   playerStatsTimer = null
let   playerPositionsTimer = null
let   dashMapRefreshTimer = null
const minimapCanvas   = ref(null)
const minimapViewport = ref(null)
const dashMapImg      = ref(null)   // Base64 编码的 PNG 字符串
const dashMapEl       = ref(null)   // 已加载的 HTMLImageElement
const dashMapW        = ref(0)
const dashMapH        = ref(0)
const loadingDashMap  = ref(false)
const mapZoom         = ref(1)
const mapPanX         = ref(0)
const mapPanY         = ref(0)
const mapDragging     = ref(false)
const selectedPlayer  = ref(null)
let   pendingDashMapId = null
let   pendingDashMapSilent = false
let   _dragStartX = 0, _dragStartY = 0, _panStartX = 0, _panStartY = 0

const _colorCache = {}
function getPlayerColor(name) {
  if (_colorCache[name]) return _colorCache[name]
  let hash = 0
  for (const c of name) hash = ((hash << 5) - hash + c.charCodeAt(0)) | 0
  _colorCache[name] = `hsl(${Math.abs(hash) % 360}, 80%, 60%)`
  return _colorCache[name]
}

function resolveDd2Display(t1, t2, t3) {
  // 事件显示阶段规则：
  // 未完成 -> 显示 T1；完成 T1 -> 显示 T2；完成 T2 -> 显示 T3；
  // 只要 T3 为 true 就视为通关（兼容偶发跳过 T2 标记的情况）。
  if (t3) {
    return { label: '撒旦军队（T3）', icon: '双足翼龙', done: true }
  }
  if (t2) {
    return { label: '撒旦军队（T3）', icon: '双足翼龙', done: false }
  }
  if (t1) {
    return { label: '撒旦军队（T2）', icon: '食人魔', done: false }
  }
  return { label: '撒旦军队（T1）', icon: '黑暗魔法师', done: false }
}

const bossProgressList = computed(() => {
  const payloadItems = worldProgress.value?.progress_items
  if (Array.isArray(payloadItems) && payloadItems.length > 0) {
    const dd2StageMap = new Map(payloadItems
      .filter((item) => {
        const k = String(item?.key || '')
        return k === 'old_ones_army_t1' || k === 'old_ones_army_t2' || k === 'old_ones_army_t3'
      })
      .map((item) => [String(item?.key || ''), !!item?.done]))

    const dd2T1 = dd2StageMap.get('old_ones_army_t1') || false
    const dd2T2 = dd2StageMap.get('old_ones_army_t2') || false
    const dd2T3 = dd2StageMap.get('old_ones_army_t3') || false

    const list = payloadItems
      .filter((item) => {
        const k = String(item?.key || '')
        return k !== 'old_ones_army_t1' && k !== 'old_ones_army_t2' && k !== 'old_ones_army_t3' && k !== 'old_ones_army'
      })
      .map((item, idx) => {
      const label = String(item?.name || item?.label || `进度项${idx + 1}`)
      return {
        key: String(item?.key || `progress_${idx}`),
        label,
        icon: label,
        done: !!item?.done,
      }
    })

    const dd2Display = resolveDd2Display(dd2T1, dd2T2, dd2T3)
    const dd2Item = {
      key: 'old_ones_army',
      label: dd2Display.label,
      icon: dd2Display.icon,
      done: dd2Display.done,
    }

    const insertAfterKey = 'golem'
    const insertIndex = list.findIndex((x) => x.key === insertAfterKey)
    if (insertIndex >= 0) {
      list.splice(insertIndex + 1, 0, dd2Item)
    } else {
      list.push(dd2Item)
    }

    return list
  }

  const isCrimson = !!worldProgress.value?.is_crimson
  return [
    { key: 'king_slime', label: '史莱姆王', icon: '史莱姆王', done: !!worldProgress.value?.king_slime },
    { key: 'eye_of_cthulhu', label: '克苏鲁之眼', icon: '克苏鲁之眼', done: !!worldProgress.value?.eye_of_cthulhu },
    { key: 'goblins', label: '哥布林入侵', icon: '哥布林入侵', done: !!worldProgress.value?.goblins },
    { key: 'eater_of_worlds', label: '世界吞噬怪', icon: '世界吞噬怪', done: !isCrimson && !!worldProgress.value?.eow_or_boc },
    { key: 'brain_of_cthulhu', label: '克苏鲁之脑', icon: '克苏鲁之脑', done: isCrimson && !!worldProgress.value?.eow_or_boc },
    { key: 'queen_bee', label: '蜂王', icon: '蜂王', done: !!worldProgress.value?.queen_bee },
    { key: 'deerclops', label: '独眼巨鹿', icon: '独眼巨鹿', done: !!worldProgress.value?.deerclops },
    { key: 'skeletron', label: '骷髅王', icon: '骷髅王', done: !!worldProgress.value?.skeletron },
    { key: 'wall_of_flesh', label: '血肉墙', icon: '血肉墙', done: !!worldProgress.value?.wall_of_flesh },
    { key: 'frost', label: '雪人军团', icon: '雪人军团', done: !!worldProgress.value?.frost },
    { key: 'pirates', label: '海盗入侵', icon: '海盗入侵', done: !!worldProgress.value?.pirates },
    { key: 'queen_slime', label: '史莱姆皇后', icon: '史莱姆皇后', done: !!worldProgress.value?.queen_slime },
    { key: 'the_twins', label: '双子魔眼', icon: '双子魔眼', done: !!worldProgress.value?.the_twins },
    { key: 'the_destroyer', label: '毁灭者', icon: '毁灭者', done: !!worldProgress.value?.the_destroyer },
    { key: 'skeletron_prime', label: '机械骷髅王', icon: '机械骷髅王', done: !!worldProgress.value?.skeletron_prime },
    { key: 'plantera', label: '世纪之花', icon: '世纪之花', done: !!worldProgress.value?.plantera },
    { key: 'halloween_king', label: '南瓜月', icon: '南瓜月', done: !!worldProgress.value?.halloween_king },
    { key: 'christmas_ice_queen', label: '冰霜月', icon: '冰霜月', done: !!worldProgress.value?.christmas_ice_queen },
    { key: 'golem', label: '石巨人', icon: '石巨人', done: !!worldProgress.value?.golem },
    {
      key: 'old_ones_army',
      label: resolveDd2Display(
        !!worldProgress.value?.old_ones_army_t1,
        !!worldProgress.value?.old_ones_army_t2,
        !!worldProgress.value?.old_ones_army_t3,
      ).label,
      icon: resolveDd2Display(
        !!worldProgress.value?.old_ones_army_t1,
        !!worldProgress.value?.old_ones_army_t2,
        !!worldProgress.value?.old_ones_army_t3,
      ).icon,
      done: resolveDd2Display(
        !!worldProgress.value?.old_ones_army_t1,
        !!worldProgress.value?.old_ones_army_t2,
        !!worldProgress.value?.old_ones_army_t3,
      ).done,
    },
    { key: 'martians', label: '火星暴乱', icon: '火星暴乱', done: !!worldProgress.value?.martians },
    { key: 'duke_fishron', label: '猪龙鱼公爵', icon: '猪龙鱼公爵', done: !!worldProgress.value?.duke_fishron },
    { key: 'empress_of_light', label: '光之女皇', icon: '光之女皇', done: !!worldProgress.value?.empress_of_light },
    { key: 'lunatic_cultist', label: '拜月教邪教徒', icon: '拜月教邪教徒', done: !!worldProgress.value?.lunatic_cultist },
    { key: 'tower_solar', label: '日耀柱', icon: '日耀柱', done: !!worldProgress.value?.tower_solar },
    { key: 'tower_vortex', label: '星旋柱', icon: '星旋柱', done: !!worldProgress.value?.tower_vortex },
    { key: 'tower_nebula', label: '星云柱', icon: '星云柱', done: !!worldProgress.value?.tower_nebula },
    { key: 'tower_stardust', label: '星尘柱', icon: '星尘柱', done: !!worldProgress.value?.tower_stardust },
    { key: 'moon_lord', label: '月亮领主', icon: '月亮领主', done: !!worldProgress.value?.moon_lord },
  ]
})

const worldDifficultyLabel = computed(() => {
  if (!worldProgress.value) return '普通'
  if (worldProgress.value.world_difficulty) return String(worldProgress.value.world_difficulty)
  if (worldProgress.value.is_legendary) return '传奇'
  if (worldProgress.value.is_journey) return '旅途'
  if (worldProgress.value.is_master) return '大师'
  if (worldProgress.value.is_expert) return '专家'
  return '普通'
})

function bossIconUrl(boss) {
  const key = String(boss?.key || '').trim()
  const icon = String(boss?.icon || boss?.label || '').trim()
  const rawBase = import.meta.env.BASE_URL || '/'
  const base = rawBase.endsWith('/') ? rawBase : `${rawBase}/`

  // 将展示名称对齐到 Web/public/Boss 目录中的真实文件名。
  const aliasByKey = {
    king_slime: '史莱姆王',
    eye_of_cthulhu: '克苏鲁之眼',
    goblins: '哥布林军队',
    eater_of_worlds: '世界吞噬怪',
    brain_of_cthulhu: '克苏鲁之脑',
    queen_bee: '蜂王',
    deerclops: '鹿角怪',
    skeletron: '骷髅王',
    wall_of_flesh: '血肉墙',
    frost: '雪人军团',
    pirates: '海盗入侵',
    queen_slime: '史莱姆皇后',
    the_twins: '双子魔眼',
    the_destroyer: '毁灭者',
    skeletron_prime: '机械骷髅王',
    plantera: '世纪之花',
    halloween_king: '南瓜月',
    christmas_ice_queen: '霜月',
    golem: '石巨人',
    martians: '火星暴乱',
    duke_fishron: '猪龙鱼公爵',
    empress_of_light: '光之女皇',
    lunatic_cultist: '拜月教邪教徒',
    tower_solar: '日耀柱',
    tower_vortex: '星旋柱',
    tower_nebula: '星云柱',
    tower_stardust: '星尘柱',
    moon_lord: '月亮领主',
    old_ones_army_t1: '黑暗魔法师',
    old_ones_army_t2: '食人魔',
    old_ones_army_t3: '双足翼龙',
  }

  const aliasByName = {
    哥布林入侵: '哥布林军队',
    独眼巨鹿: '鹿角怪',
    冰霜月: '霜月',
    撒旦军队: '黑暗魔法师',
  }

  // 对 old_ones_army 优先使用按阶段动态切换的图标（T1/T2/T3）。
  const resolved = aliasByName[icon] || aliasByKey[key] || icon || '背景'
  return `${base}Boss/${encodeURIComponent(resolved)}.gif`
}

function onBossIconError(e) {
  const img = e?.target
  if (!img) return
  const stage = img.dataset.fallbackStage || 'none'
  if (stage === 'none') {
    img.dataset.fallbackStage = 'jpg'
    img.src = img.src.replace(/\.gif(\?.*)?$/i, '.jpg$1')
    return
  }
  if (stage === 'jpg') {
    img.dataset.fallbackStage = 'final'
    const rawBase = import.meta.env.BASE_URL || '/'
    const base = rawBase.endsWith('/') ? rawBase : `${rawBase}/`
    // 最终兜底使用已确认存在的文件。
    img.src = `${base}Boss/%E5%8F%B2%E8%8E%B1%E5%A7%86%E7%8E%8B.gif`
  }
}

const sortedByTime   = computed(() =>
  [...(playerStats.value || [])].sort((a, b) => b.online_seconds - a.online_seconds).slice(0, 10))
const sortedByDeaths = computed(() =>
  [...(playerStats.value || [])].sort((a, b) => b.deaths - a.deaths).slice(0, 10))

const cpuColor = computed(() => {
  const v = serverStats.value?.resources?.cpu_percent ?? 0
  if (v >= 80) return '#ef4444'
  if (v >= 50) return '#f59e0b'
  return '#22c55e'
})

function fmtTime(secs) {
  if (!secs) return '0m'
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

function fetchWorldProgress() {
  if (!activeServerKey.value) return
  sendWs({ type: 'world_progress', msg_id: Date.now().toString(), timestamp: Date.now(),
           payload: { agent_key: activeServerKey.value } })
}

function fetchPlayerStats() {
  if (!activeServerKey.value) return
  sendWs({ type: 'player_stats', msg_id: Date.now().toString(), timestamp: Date.now(),
           payload: { agent_key: activeServerKey.value } })
}

function normalizePlayerStats(rows) {
  if (!Array.isArray(rows)) return []
  return rows
    .map((r) => {
      const name = (r?.name ?? r?.Name ?? r?.player ?? r?.username ?? '').toString().trim()
      const deathsRaw = r?.deaths ?? r?.Deaths ?? 0
      const onlineRaw = r?.online_seconds ?? r?.OnlineSeconds ?? r?.onlineSeconds ?? 0
      const deaths = Number.isFinite(Number(deathsRaw)) ? Number(deathsRaw) : 0
      const onlineSeconds = Number.isFinite(Number(onlineRaw)) ? Number(onlineRaw) : 0
      return {
        name,
        deaths,
        online_seconds: onlineSeconds,
      }
    })
    .filter((r) => r.name.length > 0)
}

function startPlayerStatsPolling() {
  stopPlayerStatsPolling()
  if (!props.agentOnline || !activeServerKey.value) return
  playerStatsTimer = setInterval(() => {
    fetchPlayerStats()
  }, 15000)
}

function stopPlayerStatsPolling() {
  if (!playerStatsTimer) return
  clearInterval(playerStatsTimer)
  playerStatsTimer = null
}

function fetchPlayerPositions() {
  if (!activeServerKey.value) return
  sendWs({ type: 'get_player_positions', msg_id: `pos-${Date.now()}`, timestamp: Date.now(),
           payload: { agent_key: activeServerKey.value } })
}

function startPlayerPositionsPolling() {
  stopPlayerPositionsPolling()
  if (!props.agentOnline || !activeServerKey.value) return
  fetchPlayerPositions()
  playerPositionsTimer = setInterval(fetchPlayerPositions, 3000)
}

function stopPlayerPositionsPolling() {
  if (!playerPositionsTimer) return
  clearInterval(playerPositionsTimer)
  playerPositionsTimer = null
}

function startDashMapRefreshPolling() {
  stopDashMapRefreshPolling()
  if (!props.agentOnline || !activeServerKey.value || !canManageActiveServer.value) return
  dashMapRefreshTimer = setInterval(() => {
    if (dashMapImg.value && !loadingDashMap.value) fetchDashMap(true)
  }, 15000)
}

function stopDashMapRefreshPolling() {
  if (!dashMapRefreshTimer) return
  clearInterval(dashMapRefreshTimer)
  dashMapRefreshTimer = null
}

function drawMinimap() {
  const canvas = minimapCanvas.value
  if (!canvas) return
  const pList = serverStats.value?.players
  const world = serverStats.value?.world
  const ctx = canvas.getContext('2d')

  if (dashMapEl.value) {
    // 地图图片已加载：以真实地形为底图
    canvas.width  = dashMapEl.value.naturalWidth
    canvas.height = dashMapEl.value.naturalHeight
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(dashMapEl.value, 0, 0)
    if (pList?.length) {
      for (const p of pList) {
        // PNG 是 1/4 采样，所以 canvas 像素坐标 = tile / 4
        const px = p.tile_x / 4
        const py = p.tile_y / 4
        const isSel = selectedPlayer.value === p.name
        const color = getPlayerColor(p.name)
        ctx.shadowColor = color
        ctx.shadowBlur  = isSel ? 10 : 4
        ctx.beginPath()
        ctx.arc(px, py, isSel ? 6 : 4, 0, Math.PI * 2)
        ctx.fillStyle = color
        ctx.fill()
        ctx.strokeStyle = isSel ? '#fff' : 'rgba(0,0,0,0.7)'
        ctx.lineWidth   = isSel ? 1.5 : 0.8
        ctx.stroke()
        ctx.shadowBlur = 0
        // 名字标签
        ctx.font        = isSel ? 'bold 9px sans-serif' : '8px sans-serif'
        ctx.fillStyle   = '#fff'
        ctx.shadowColor = '#000'
        ctx.shadowBlur  = 3
        ctx.fillText(p.name, px + 7, py + 4)
        ctx.shadowBlur = 0
      }
    }
    return
  }

  // 无底图时仅渲染玩家点（白色背景）
  if (!pList?.length || !world?.width) return
  if (!canvas.width) { canvas.width = 400; canvas.height = 120 }
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.fillStyle = '#f1f5f9'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  for (const p of pList) {
    const x = (p.tile_x / world.width)  * canvas.width
    const y = (p.tile_y / world.height) * canvas.height
    const isSel = selectedPlayer.value === p.name
    ctx.beginPath()
    ctx.arc(x, y, isSel ? 6 : 4, 0, Math.PI * 2)
    ctx.fillStyle = getPlayerColor(p.name)
    ctx.fill()
    ctx.strokeStyle = isSel ? '#1e293b' : 'rgba(0,0,0,0.4)'
    ctx.lineWidth = 1.2
    ctx.stroke()
    ctx.font      = isSel ? 'bold 10px sans-serif' : '10px sans-serif'
    ctx.fillStyle = '#1e293b'
    ctx.shadowColor = '#fff'
    ctx.shadowBlur  = 2
    ctx.fillText(p.name, x + 7, y + 4)
    ctx.shadowBlur = 0
  }
}

// ── 缓存 ─────────────────────────────────────────────────────
function saveMapCache(img, w, h) {
  try {
    sessionStorage.setItem(`mmap_${activeServerKey.value}`,
      JSON.stringify({ img, w, h, ts: Date.now() }))
  } catch (_) {}
}
function loadMapCache() {
  if (!activeServerKey.value) return
  try {
    const raw = sessionStorage.getItem(`mmap_${activeServerKey.value}`)
    if (!raw) return
    const { img, w, h, ts } = JSON.parse(raw)
    if (Date.now() - ts > 30 * 60 * 1000) { sessionStorage.removeItem(`mmap_${activeServerKey.value}`); return }
    dashMapW.value = w; dashMapH.value = h; dashMapImg.value = img
    const image = new Image()
    image.onload = () => { dashMapEl.value = image; drawMinimap(); fitMapToViewport() }
    image.src = `data:image/png;base64,${img}`
  } catch (_) {}
}

// ── 地图交互 ─────────────────────────────────────────────────
async function fitMapToViewport() {
  await nextTick()
  const vp = minimapViewport.value
  const canvas = minimapCanvas.value
  if (!vp || !canvas || !canvas.width || !canvas.height) return
  const vpW = vp.clientWidth || vp.offsetWidth
  const vpH = vp.clientHeight || vp.offsetHeight
  if (!vpW || !vpH) return
  const zoom = Math.min(vpW / canvas.width, vpH / canvas.height)
  mapZoom.value = zoom
  mapPanX.value = (vpW - canvas.width  * zoom) / 2
  mapPanY.value = (vpH - canvas.height * zoom) / 2
}
function resetMapView() {
  fitMapToViewport()
}
function onMapWheel(e) {
  const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15
  const rect = minimapViewport.value.getBoundingClientRect()
  const mx = e.clientX - rect.left, my = e.clientY - rect.top
  const newZoom = Math.max(0.1, Math.min(10, mapZoom.value * factor))
  const scale = newZoom / mapZoom.value
  mapPanX.value = mx - (mx - mapPanX.value) * scale
  mapPanY.value = my - (my - mapPanY.value) * scale
  mapZoom.value = newZoom
}
function onMapMouseDown(e) {
  mapDragging.value = true
  _dragStartX = e.clientX; _dragStartY = e.clientY
  _panStartX = mapPanX.value; _panStartY = mapPanY.value
}
function onMapMouseMove(e) {
  if (!mapDragging.value) return
  mapPanX.value = _panStartX + (e.clientX - _dragStartX)
  mapPanY.value = _panStartY + (e.clientY - _dragStartY)
}
function onMapMouseUp() { mapDragging.value = false }
function onMapTouchStart(e) {
  if (e.touches.length === 2) {
    // 双指缩放：记录初始距离
    _dragStartX = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY)
  } else if (e.touches.length === 1) {
    mapDragging.value = true
    _dragStartX = e.touches[0].clientX
    _dragStartY = e.touches[0].clientY
    _panStartX = mapPanX.value
    _panStartY = mapPanY.value
  }
}
function onMapTouchMove(e) {
  if (e.touches.length === 2) {
    const d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY)
    if (_dragStartX > 0) {
      const factor = d / _dragStartX
      const newZoom = Math.max(0.1, Math.min(10, mapZoom.value * factor))
      const rect = minimapViewport.value.getBoundingClientRect()
      const cx = ((e.touches[0].clientX + e.touches[1].clientX) / 2) - rect.left
      const cy = ((e.touches[0].clientY + e.touches[1].clientY) / 2) - rect.top
      const scale = newZoom / mapZoom.value
      mapPanX.value = cx - (cx - mapPanX.value) * scale
      mapPanY.value = cy - (cy - mapPanY.value) * scale
      mapZoom.value = newZoom
      _dragStartX = d
    }
  } else if (e.touches.length === 1 && mapDragging.value) {
    mapPanX.value = _panStartX + (e.touches[0].clientX - _dragStartX)
    mapPanY.value = _panStartY + (e.touches[0].clientY - _dragStartY)
  }
}
function onMapTouchEnd() { mapDragging.value = false; _dragStartX = 0 }
function onViewportClick(e) {
  if (Math.abs(e.clientX - _dragStartX) > 5 || Math.abs(e.clientY - _dragStartY) > 5) return
  if (!dashMapEl.value) return
  const rect = minimapViewport.value.getBoundingClientRect()
  const cx = (e.clientX - rect.left - mapPanX.value) / mapZoom.value
  const cy = (e.clientY - rect.top  - mapPanY.value) / mapZoom.value
  const pList = serverStats.value?.players
  if (!pList?.length) return
  let nearest = null, minDist = Infinity
  for (const p of pList) {
    const dist = Math.hypot(p.tile_x / 4 - cx, p.tile_y / 4 - cy)
    if (dist < minDist) { minDist = dist; nearest = p.name }
  }
  selectedPlayer.value = minDist < 15 / mapZoom.value ? (selectedPlayer.value === nearest ? null : nearest) : null
  drawMinimap()
}
function toggleSelectPlayer(name) {
  selectedPlayer.value = selectedPlayer.value === name ? null : name
  drawMinimap()
}

function fetchDashMap(silent = false) {
  silent = silent === true
  if (!activeServerKey.value) return
  if (!silent) {
    loadingDashMap.value = true
    dashMapImg.value    = null
    dashMapEl.value     = null
    resetMapView()
  }
  pendingDashMapId = `dash-map-${Date.now()}`
  pendingDashMapSilent = silent
  window.__tshockSend?.({
    type: 'get_minimap', msg_id: pendingDashMapId,
    timestamp: Date.now(), payload: { agent_key: activeServerKey.value }
  })
}

// ── 玩家操作面板 ─────────────────────────────────────────────────
const papVisible    = ref(false)
const papSscEnabled = ref(false)
const papPlayer     = ref({ name: '', email: '', group: '', hp: 0, maxHp: 0, mana: 0, maxMana: 0, ownerUserId: null, allChars: [] })
const papIsBanned   = ref(false)
const papBanTicket  = ref(0)
const papRef        = ref(null)
const dashMembers   = ref([])
const dashCharMap   = ref({})
const papAssignOwnerOptions = computed(() =>
  dashMembers.value.map((m) => ({ user_id: m.user_id, email: m.email }))
)
let   papInvReqId   = null
let   papBanReqId   = null

async function loadDashboardOwnershipContext() {
  dashMembers.value = []
  dashCharMap.value = {}
  const sid = activeServer.value?.id
  if (!sid || !canManageActiveServer.value) return
  try {
    const headers = { Authorization: `Bearer ${getToken()}` }
    const [srvRes, mapRes] = await Promise.all([
      fetch(apiUrl(`/api/servers/${sid}`), { headers }),
      fetch(apiUrl(`/api/servers/${sid}/character-map`), { headers }),
    ])
    if (srvRes.ok) {
      const srvData = await srvRes.json()
      dashMembers.value = srvData.members || []
    }
    if (mapRes.ok) {
      dashCharMap.value = await mapRes.json()
    }
  } catch {
    // 归属数据加载失败不应影响仪表盘主流程
  }
}

function openPlayerPanel(p) {
  const ownerEmail = dashCharMap.value[p.name] || ''
  const ownerUserId = ownerEmail
    ? (dashMembers.value.find((m) => m.email === ownerEmail)?.user_id ?? null)
    : null
  const allChars = ownerEmail
    ? Object.entries(dashCharMap.value)
      .filter(([, email]) => email === ownerEmail)
      .map(([name]) => name)
    : []
  papPlayer.value = {
    name: p.name,
    email: ownerEmail,
    group: p.group || '',
    hp: p.hp || 0,
    maxHp: p.max_hp || 0,
    mana: p.mana || 0,
    maxMana: p.max_mana || 0,
    ownerUserId,
    allChars,
  }
  papSscEnabled.value = false
  papIsBanned.value = false
  papBanTicket.value = 0
  papVisible.value = true
  // 拉背包数据获取 ssc_enabled
  papInvReqId = `pap-${Date.now()}`
  window.__tshockSend?.({ type: 'get_inventory', msg_id: papInvReqId, timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, username: p.name } })

  papBanReqId = `pab-${Date.now()}`
  window.__tshockSend?.({
    type: 'player_action', msg_id: papBanReqId, timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, action: 'ban_status', player: p.name },
  })
}

function handlePapAction(evt) {
  if (!activeServerKey.value) {
    papRef.value?.showResult(false, '未选择服务器')
    return
  }
  const reqId = `pa-${Date.now()}`
  const reason = (evt?.reason || '').trim() || '由管理员操作'
  const duration = (evt?.duration || '').trim()
  const sent = window.__tshockSend?.({ type: 'player_action', msg_id: reqId, timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, ...evt, reason, duration } })
  if (!sent) {
    papRef.value?.showResult(false, 'WebSocket 未连接，无法发送操作')
    return
  }
  let settled = false
  const handler = (e) => {
    const pkt = e.detail || {}
    if (pkt.type !== 'player_action_resp') return
    const p = pkt.payload || {}
    if (p.ref_id !== reqId) return
    settled = true
    window.removeEventListener('ws-message', handler)
    papRef.value?.showResult(!!p.success, p.msg || (p.success ? '操作成功' : '操作失败'))
  }
  window.addEventListener('ws-message', handler)
  setTimeout(() => {
    window.removeEventListener('ws-message', handler)
    if (!settled) papRef.value?.showResult(false, '操作超时，请确认 Agent 在线')
  }, 15000)
}

function handleRequestGroups() {
  if (!activeServerKey.value) {
    papRef.value?.setAvailableGroups([])
    papRef.value?.showResult(false, '未选择服务器')
    return
  }
  const sent = window.__tshockSend?.({
    type: 'get_groups',
    msg_id: `gg-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
  if (!sent) {
    papRef.value?.setAvailableGroups([])
    papRef.value?.showResult(false, 'WebSocket 未连接，无法获取权限组')
  }
}

function handlePapBanAll({ chars, reason, duration }) {
  if (!activeServerKey.value) {
    papRef.value?.showResult(false, '未选择服务器')
    return
  }
  const reqId = `pba-${Date.now()}`
  const banReason = (reason || '').trim() || '由管理员一键封禁'
  const banDuration = (duration || '').trim()
  const sent = window.__tshockSend?.({ type: 'player_action', msg_id: reqId, timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, action: 'ban_all', player: '', chars, reason: banReason, duration: banDuration } })
  if (!sent) {
    papRef.value?.showResult(false, 'WebSocket 未连接，无法发送操作')
    return
  }
  let settled = false
  const handler = (e) => {
    const pkt = e.detail || {}
    if (pkt.type !== 'player_action_resp') return
    const p = pkt.payload || {}
    if (p.ref_id !== reqId) return
    settled = true
    window.removeEventListener('ws-message', handler)
    papRef.value?.showResult(!!p.success, p.msg || '操作完成')
  }
  window.addEventListener('ws-message', handler)
  setTimeout(() => {
    window.removeEventListener('ws-message', handler)
    if (!settled) papRef.value?.showResult(false, '操作超时，请确认 Agent 在线')
  }, 15000)
}

async function handlePapAssignOwner({ player, user_id }) {
  const sid = activeServer.value?.id
  if (!sid || !player) return
  const targetUserId = (user_id == null || user_id === '') ? null : Number(user_id)
  if (targetUserId != null && (!Number.isFinite(targetUserId) || targetUserId <= 0)) {
    papRef.value?.showResult(false, '目标归属账号无效')
    return
  }
  try {
    const resp = await assignCharacterOwner(sid, {
      character_name: player,
      target_user_id: targetUserId,
    })
    const actionText = {
      created: '已分配给',
      reassigned: '已改归属为',
      unchanged: '归属未变化，当前为',
      cleared: '已清除归属，当前为',
    }[resp.action] || '已设置归属为'
    const nextEmail = resp.target_email || ''
    const nextOwnerId = resp.target_user_id == null ? null : Number(resp.target_user_id)
    papPlayer.value = {
      ...papPlayer.value,
      email: nextEmail,
      ownerUserId: nextOwnerId,
      allChars: nextEmail
        ? Array.from(new Set([...(papPlayer.value.allChars || []), player]))
        : (papPlayer.value.allChars || []).filter(c => c !== player),
    }
    papRef.value?.showResult(true, `${actionText} ${nextEmail || '无'}`)
    await loadDashboardOwnershipContext()
  } catch (e) {
    papRef.value?.showResult(false, e.message || '分配失败')
  }
}

async function handlePapDeleteAccount({ player }) {
  const sid = activeServer.value?.id
  if (!sid || !player) return
  try {
    let resp = null
    const ownerId = Number(papPlayer.value?.ownerUserId)

    if (Number.isFinite(ownerId) && ownerId > 0) {
      try {
        await deleteMemberCharacter(sid, ownerId, player)
        resp = {
          removed_binding: true,
          agent_dispatched: true,
        }
      } catch (primaryErr) {
        try {
          resp = await deleteGameAccount(sid, player)
        } catch {
          throw primaryErr
        }
      }
    } else {
      resp = await deleteGameAccount(sid, player)
    }

    const msgParts = []
    if (resp.removed_binding) msgParts.push('绑定已删除')
    else msgParts.push('未发现绑定记录')
    if (resp.agent_dispatched) msgParts.push('已请求删除游戏账号')
    if (resp.agent_warning) msgParts.push(resp.agent_warning)
    papRef.value?.showResult(true, msgParts.join('，'))
    await loadDashboardOwnershipContext()
  } catch (e) {
    papRef.value?.showResult(false, e.message || '删除账号失败')
  }
}

// ── 背包（composable）──────────────────────────────────────────────
const {
  invVisible, invUsername, invLoading, invError,
  invSlots, invHealth, invMaxHealth, invMana, invMaxMana,
  invIsOnline, invSscEnabled, invSaving,
  openInventory: _openInv,
  handleSaveInventory: _handleSaveInv,
  consumeWsMessage: consumeInvMsg,
} = useInventory()
function openInventory(name) { _openInv(name, activeServerKey.value) }
function onSaveInventory(slotMap) { _handleSaveInv(slotMap, activeServerKey.value) }

function mergePlayerRuntime(players, world = null) {
  if (!Array.isArray(players)) return
  const previous = new Map((serverStats.value?.players || []).map((p) => [p.name, p]))
  const mergedPlayers = players.map((p) => ({
    ...(previous.get(p.name) || {}),
    ...p,
  }))
  serverStats.value = {
    ...(serverStats.value || {}),
    online_players: mergedPlayers.length,
    players: mergedPlayers,
    ...(world ? { world } : {}),
  }
  drawMinimap()
}

function onWsMessage(e) {
  const pkt = e.detail
  if (pkt.type === 'server_ctrl_resp') {
    stopping.value  = false
    restarting.value = false
  } else if (pkt.type === 'status') {
    const meta = pkt.metadata?.agent_key
    if (!meta || meta === activeServerKey.value) {
      serverStats.value = pkt.payload || null
      drawMinimap()
    }
  } else if (pkt.type === 'minimap_resp') {
    const meta = pkt.metadata?.agent_key
    if (meta && meta !== activeServerKey.value) return
    loadingDashMap.value = false
    if (pkt.payload?.ref_id !== pendingDashMapId) return
    const silentMapRefresh = pendingDashMapSilent
    pendingDashMapId = null
    pendingDashMapSilent = false
    if (!pkt.payload?.success) { console.warn('[Dashboard minimap]', pkt.payload?.msg); return }
    dashMapW.value = pkt.payload.world_width
    dashMapH.value = pkt.payload.world_height
    dashMapImg.value = pkt.payload.img
    saveMapCache(pkt.payload.img, pkt.payload.world_width, pkt.payload.world_height)
    const img = new Image()
    img.onload = () => {
      dashMapEl.value = img
      drawMinimap()
      if (!silentMapRefresh) fitMapToViewport()
    }
    img.src = `data:image/png;base64,${pkt.payload.img}`
    if (pkt.payload.players) {
      mergePlayerRuntime(
        pkt.payload.players,
        { width: pkt.payload.world_width, height: pkt.payload.world_height }
      )
    }
  } else if (pkt.type === 'world_progress_resp') {
    if (pkt.payload?.success) worldProgress.value = pkt.payload.progress
  } else if (pkt.type === 'player_stats_resp') {
    if (pkt.payload?.success) playerStats.value = normalizePlayerStats(pkt.payload.stats)
  } else if (pkt.type === 'player_positions_resp') {
    const meta = pkt.metadata?.agent_key
    if (meta && meta !== activeServerKey.value) return
    if (pkt.payload?.success) {
      mergePlayerRuntime(
        pkt.payload.players,
        { width: pkt.payload.world_width, height: pkt.payload.world_height }
      )
    }
  } else if (pkt.type === 'get_inventory_resp') {
    const p = pkt.payload || {}
    // 玩家操作面板拉取 ssc 信息
    if (papInvReqId && p.ref_id === papInvReqId) {
      papInvReqId = null
      papSscEnabled.value = !!p.ssc_enabled
    }
    // 背包模态框
    consumeInvMsg(pkt)
  } else if (pkt.type === 'save_inventory_resp') {
    consumeInvMsg(pkt)
  } else if (pkt.type === 'player_action_resp') {
    const p = pkt.payload || {}
    if (papBanReqId && p.ref_id === papBanReqId && p.action === 'ban_status') {
      papBanReqId = null
      papIsBanned.value = !!p.banned
      papBanTicket.value = Number(p.ticket || 0)
    }
  } else if (pkt.type === 'get_groups_resp') {
    const meta = pkt.metadata?.agent_key
    if (meta && meta !== activeServerKey.value) return
    const p = pkt.payload || {}
    papRef.value?.setAvailableGroups(p.groups || [])
    if (!p.success) papRef.value?.showResult(false, p.msg || '获取权限组失败')
  }
}

watch(() => props.agentOnline, (val) => {
  if (val && activeServerKey.value) {
    fetchStatus()
    fetchWorldProgress()
    fetchPlayerStats()
    startPlayerStatsPolling()
    startPlayerPositionsPolling()
    startDashMapRefreshPolling()
  } else if (!val) {
    stopPlayerStatsPolling()
    stopPlayerPositionsPolling()
    stopDashMapRefreshPolling()
    serverStats.value    = null
    worldProgress.value  = null
    playerStats.value    = null
    dashMapImg.value     = null
    dashMapEl.value      = null
    loadingDashMap.value = false
    selectedPlayer.value = null
    resetMapView()
  }
})

watch(activeServerKey, () => {
  serverStats.value   = null
  worldProgress.value = null
  playerStats.value   = null
  confirmStop.value   = false
  stopping.value      = false
  restarting.value    = false
  localCfgDirty.value = false
  localCfgMsg.value   = ''
  dashMapImg.value     = null
  dashMapEl.value      = null
  loadingDashMap.value = false
  pendingDashMapId     = null
  pendingDashMapSilent = false
  selectedPlayer.value = null
  resetMapView()
  stopPlayerPositionsPolling()
  stopDashMapRefreshPolling()
  if (props.agentOnline && activeServerKey.value) {
    fetchStatus()
    fetchWorldProgress()
    fetchPlayerStats()
    startPlayerStatsPolling()
    startPlayerPositionsPolling()
    startDashMapRefreshPolling()
    nextTick(() => loadMapCache())
  } else {
    stopPlayerStatsPolling()
  }
  loadDashboardOwnershipContext()
})

watch([activeServer, canManageActiveServer], () => {
  loadDashboardOwnershipContext()
  if (props.agentOnline && activeServerKey.value) startDashMapRefreshPolling()
  else stopDashMapRefreshPolling()
})

onMounted(() => {
  window.addEventListener('ws-message', onWsMessage)
  loadMapCache()
  loadDashboardOwnershipContext()
  if (props.agentOnline && activeServerKey.value) {
    fetchStatus()
    fetchWorldProgress()
    fetchPlayerStats()
    startPlayerStatsPolling()
    startPlayerPositionsPolling()
    startDashMapRefreshPolling()
  }
})
onUnmounted(() => {
  stopPlayerStatsPolling()
  stopPlayerPositionsPolling()
  stopDashMapRefreshPolling()
  window.removeEventListener('ws-message', onWsMessage)
})

const statCards = computed(() => [
  {
    label: '在线玩家',
    value: serverStats.value
      ? `${serverStats.value.online_players}/${serverStats.value.max_players}`
      : (props.agentOnline ? '…' : '–'),
    icon: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    bg: '#f0fdf4',
  },
  {
    label: '世界',
    value: serverStats.value?.world_name || (props.agentOnline ? '…' : '–'),
    icon: '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    bg: '#eff6ff',
  },
])
</script>

<style scoped>
.dashboard {
  padding: 28px 32px;
  overflow-y: auto;
  height: 100%;
  box-sizing: border-box;
}

/* ── 引导卡片 ── */
.onboarding-card {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  background: linear-gradient(135deg, #fefce8 0%, #fef3c7 100%);
  border: 1px solid #fde68a;
  border-radius: 14px;
  padding: 22px 26px;
  margin-bottom: 24px;
}
.oc-icon { font-size: 2.2rem; flex-shrink: 0; margin-top: 2px; }
.oc-body h3 { margin: 0 0 6px; font-size: 1rem; font-weight: 700; color: #78350f; }
.oc-body p  { margin: 0 0 14px; font-size: 0.85rem; color: #92400e; line-height: 1.55; }
.btn-goto {
  display: inline-block;
  padding: 7px 18px;
  background: #f59e0b;
  color: #fff;
  border-radius: 7px;
  font-size: 0.85rem;
  font-weight: 600;
  text-decoration: none;
  transition: background .15s;
}
.btn-goto:hover { background: #d97706; }

/* ── 欢迎横幅 ── */
.welcome-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border: 1px solid #bfdbfe;
  border-radius: 14px;
  padding: 24px 28px;
  margin-bottom: 24px;
}
.welcome-text h1 {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
}
.welcome-text p {
  margin: 0;
  font-size: 14px;
  color: #64748b;
}

.server-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  border: 1px solid transparent;
}
.server-badge.online  { background: #f0fdf4; color: #16a34a; border-color: #bbf7d0; }
.server-badge.offline { background: #f8fafc; color: #94a3b8; border-color: #e2e8f0; }
.server-badge .dot {
  width: 8px; height: 8px; border-radius: 50%;
}
.online  .dot { background: #22c55e; box-shadow: 0 0 6px #22c55e; }
.offline .dot { background: #cbd5e1; }

/* ── 状态卡片 ── */
.card-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  margin-bottom: 28px;
}
.stat-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 18px;
  display: flex;
  align-items: center;
  gap: 14px;
}
.stat-icon {
  width: 44px; height: 44px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.stat-icon svg { width: 20px; height: 20px; color: #64748b; }
.stat-value { font-size: 18px; font-weight: 700; color: #0f172a; }
.stat-label { font-size: 12px; color: #94a3b8; margin-top: 2px; }

/* ── 服务器控制面板 ── */
.ctrl-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 20px 24px;
  margin-bottom: 24px;
  gap: 20px;
  flex-wrap: wrap;
}
.ctrl-left  { display: flex; flex-direction: column; gap: 5px; }
.ctrl-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }

.ctrl-label { font-size: 11px; font-weight: 700; color: #94a3b8; letter-spacing: .06em; text-transform: uppercase; }
.ctrl-name  { font-size: 16px; font-weight: 700; color: #0f172a; }

.ctrl-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px; font-weight: 600;
  width: fit-content;
}
.badge-on  { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.badge-off { background: #f8fafc; color: #94a3b8; border: 1px solid #e2e8f0; }
.ctrl-dot  { width: 7px; height: 7px; border-radius: 50%; }
.badge-on  .ctrl-dot { background: #22c55e; box-shadow: 0 0 5px #22c55e; }
.badge-off .ctrl-dot { background: #cbd5e1; }

.power-btn {
  display: flex; align-items: center; gap: 7px;
  padding: 9px 20px;
  border-radius: 8px;
  font-size: 13px; font-weight: 600;
  cursor: pointer; border: none;
  transition: all .15s;
}
.power-btn svg { width: 15px; height: 15px; }

.btn-stop    { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.btn-stop:hover:not(:disabled) { background: #fee2e2; }
.btn-stop:disabled { opacity: .45; cursor: not-allowed; }

.btn-stop-normal { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.btn-stop-normal:hover { background: #dcfce7; }
.btn-stop-nosave { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
.btn-stop-nosave:hover { background: #ffedd5; }
.btn-cancel  { background: #f1f5f9; color: #475569; }
.btn-cancel:hover  { background: #e2e8f0; }

.confirm-text { font-size: 13px; font-weight: 600; color: #b45309; }
.ctrl-hint    { font-size: 12px; color: #94a3b8; }

.offline-hint {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; color: #94a3b8;
}
.offline-hint svg { width: 16px; height: 16px; color: #cbd5e1; }

/* ── 说明 ── */
.notice {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 14px 18px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
}
.notice-icon { width: 16px; height: 16px; flex-shrink: 0; margin-top: 2px; color: #3b82f6; }

/* ── section-title badge ── */
.section-badge {
  font-size: 12px; font-weight: 600;
  padding: 2px 8px;
  background: #e0f2fe; color: #0369a1;
  border-radius: 20px;
}
.section-badge-owner { background: #fef3c7; color: #92400e; }

/* ── 资源监控 ── */
.resource-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 24px;
}
.resource-card {
  background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px 20px;
}
.rc-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.rc-label { font-size: 13px; color: #64748b; font-weight: 500; }
.rc-value { font-size: 18px; font-weight: 700; }
.rc-bar-wrap { height: 6px; background: #f1f5f9; border-radius: 99px; overflow: hidden; }
.rc-bar { height: 100%; border-radius: 99px; transition: width .5s ease; }

/* ── 在线玩家列表 ── */
.player-list {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px; margin-bottom: 16px;
}
.player-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 16px; }
.pc-name-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.pc-name { font-size: 14px; font-weight: 700; color: #1e293b; }
.pc-more-btn {
  background: none; border: none; cursor: pointer; padding: 3px 5px;
  border-radius: 5px; color: #94a3b8; display: flex; align-items: center;
}
.pc-more-btn:hover { background: #f1f5f9; color: #0f172a; }
.pc-bars { display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px; }
.pc-bar-row { display: flex; align-items: center; gap: 6px; }
.pc-bar-icon { font-size: 11px; width: 14px; flex-shrink: 0; }
.pc-bar-icon.hp { color: #ef4444; }
.pc-bar-icon.mp { color: #6366f1; font-size: 9px; }
.pc-bar-track { flex: 1; height: 5px; background: #f1f5f9; border-radius: 99px; overflow: hidden; }
.pc-bar-fill { height: 100%; border-radius: 99px; transition: width .5s ease; }
.pc-bar-fill.hp { background: #ef4444; }
.pc-bar-fill.mp { background: #6366f1; }
.pc-bar-txt { font-size: 11px; color: #94a3b8; width: 58px; text-align: right; flex-shrink: 0; }
.pc-pos { font-size: 11px; color: #94a3b8; margin-top: 4px; }

/* ── 玩家卡片高亮 ── */
.player-card-sel {
  border-color: #93c5fd !important;
  box-shadow: 0 0 0 2px #dbeafe;
  background: #eff6ff !important;
}

/* ── 小地图 ── */
.minimap-wrap {
  margin: 8px 0 24px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.minimap-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; background: #f8fafc; border-bottom: 1px solid #e2e8f0;
}
.mm-title-icon { width: 14px; height: 14px; margin-right: 6px; vertical-align: middle; color: #64748b; }
.minimap-title { font-size: 13px; font-weight: 600; color: #374151; display: flex; align-items: center; }
.minimap-header-right { display: flex; align-items: center; gap: 8px; }
.minimap-gen-btn {
  font-size: 12px; padding: 4px 14px; background: #3b82f6; border: none;
  border-radius: 6px; color: #fff; cursor: pointer; transition: background 0.15s; font-weight: 500;
}
.minimap-gen-btn:hover:not(:disabled) { background: #2563eb; }
.minimap-gen-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.minimap-loading-txt { font-size: 12px; color: #6b7280; }
/* 缩放按钮组 */
.minimap-zoom-btns { display: flex; align-items: center; gap: 4px; background: #f1f5f9; border-radius: 7px; padding: 2px 4px; border: 1px solid #e2e8f0; }
.mz-btn {
  width: 22px; height: 22px; border: none; background: transparent; border-radius: 4px;
  cursor: pointer; font-size: 14px; line-height: 1; color: #374151; display: flex; align-items: center; justify-content: center;
  transition: background 0.1s;
}
.mz-btn:hover { background: #e2e8f0; }
.mz-reset { font-size: 11px; }
.mz-label { font-size: 11px; color: #6b7280; min-width: 32px; text-align: center; }
/* 主体：地图视口 + 玩家侧边栏 */
.minimap-body { display: flex; }
.minimap-viewport {
  flex: 1; overflow: hidden; position: relative;
  height: 280px; background: #f1f5f9;
  user-select: none;
}
.minimap-canvas { display: block; image-rendering: pixelated; }
.minimap-placeholder {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: 12px; color: #94a3b8; padding: 20px; text-align: center;
}


/* ── 进度 + 排行 双列 ── */
.bottom-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 28px; }
.bottom-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 20px 22px; }
.bc-head { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.bc-title { font-size: 15px; font-weight: 700; color: #1e293b; flex: 1; }
.bc-refresh {
  font-size: 16px; background: none; border: none; cursor: pointer;
  color: #94a3b8; padding: 2px 5px; border-radius: 4px;
}
.bc-refresh:hover { color: #3b82f6; background: #eff6ff; }
.bc-load-btn {
  font-size: 13px; padding: 7px 15px;
  background: #f8fafc; border: 1px solid #e2e8f0;
  border-radius: 7px; cursor: pointer; color: #475569; margin-top: 4px;
}
.bc-load-btn:hover { background: #eff6ff; border-color: #93c5fd; color: #3b82f6; }

.world-mode-tag {
  font-size: 13px; font-weight: 600; color: #b45309; background: #fef3c7;
  border-radius: 6px; padding: 4px 12px; display: inline-block; margin-bottom: 12px;
}
.world-mode-tag.normal { color: #166534; background: #dcfce7; }
.world-progress-summary {
  font-size: 13px;
  color: #334155;
  font-weight: 600;
  margin-bottom: 10px;
}
.boss-list { display: flex; flex-direction: column; gap: 9px; max-height: 520px; overflow-y: auto; }
.boss-item { display: flex; align-items: center; gap: 14px; font-size: 17px; color: #94a3b8; padding: 6px 0; min-height: 74px; }
.boss-item.done { color: #1e293b; }
.boss-icon {
  width: 64px;
  height: 64px;
  object-fit: contain;
  object-position: center;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  flex-shrink: 0;
}
.boss-check { font-size: 22px; line-height: 1; }
.boss-name  { font-size: 18px; font-weight: 700; }

.lb-tabs { display: flex; gap: 4px; }
.lb-tab {
  font-size: 12px; padding: 4px 10px; border-radius: 6px;
  border: 1px solid #e2e8f0; background: #f8fafc; color: #475569;
  cursor: pointer; transition: all .15s;
}
.lb-tab.active { background: #3b82f6; color: #fff; border-color: #3b82f6; }
.lb-list { display: flex; flex-direction: column; gap: 3px; max-height: 340px; overflow-y: auto; }
.lb-row {
  display: flex; align-items: center; gap: 10px;
  padding: 7px 0; border-bottom: 1px solid #f1f5f9;
}
.lb-rank { font-size: 13px; font-weight: 700; color: #94a3b8; width: 22px; text-align: center; flex-shrink: 0; }
.lb-rank.top0 { color: #f59e0b; }
.lb-rank.top1 { color: #94a3b8; }
.lb-rank.top2 { color: #b45309; }
.lb-name { flex: 1; font-size: 14px; color: #1e293b; }
.lb-val  { font-size: 13px; color: #475569; font-weight: 600; }

.empty-hint { font-size: 13px; color: #94a3b8; padding: 12px 0; display: flex; align-items: center; gap: 10px; }

/* ── 重启按钮 ── */
.btn-restart { background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; }
.btn-restart:hover:not(:disabled) { background: #dbeafe; }
.btn-restart:disabled { opacity: .45; cursor: not-allowed; }

/* 响应式 */
@media (max-width: 900px) {
  .card-grid { grid-template-columns: repeat(2, 1fr); }
  .bottom-grid, .resource-grid { grid-template-columns: 1fr; }
}
@media (max-width: 560px) {
  .card-grid, .player-list { grid-template-columns: 1fr; }
  .dashboard { padding: 16px; }
}
</style>
