<template>
  <div class="app-shell">
    <!-- 顶栏 -->
    <header class="topbar">
      <div class="topbar-left">
        <button class="sidebar-toggle" @click="sidebarOpen = !sidebarOpen" title="展开/收起侧边栏">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="3" y1="6"  x2="21" y2="6"/>
            <line x1="3" y1="12" x2="21" y2="12"/>
            <line x1="3" y1="18" x2="21" y2="18"/>
          </svg>
        </button>
        <span class="logo-icon"></span>
        <span class="site-title">TShock 管理平台</span>
      </div>
      <div class="topbar-right">
        <span :class="['status-dot', wsState]"></span>
        <span class="status-text">{{ statusText }}</span>
        <span class="user-email">{{ email }}</span>
        <button class="logout-btn" @click="handleLogout">退出</button>
      </div>
    </header>

    <div class="body-area">
      <!-- 侧边栏 -->
      <aside :class="['sidebar', { collapsed: !sidebarOpen }]">
        <nav class="nav-list">

          <!-- 固定导航 -->
          <router-link class="nav-item" to="/home" active-class="active" exact>
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5z"/>
              <polyline points="9 21 9 12 15 12 15 21"/>
            </svg>
            <span class="nav-label">主页</span>
          </router-link>

          <router-link class="nav-item" to="/servers" active-class="active">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="5" rx="1"/>
              <rect x="2" y="10" width="20" height="5" rx="1"/>
              <rect x="2" y="17" width="20" height="5" rx="1"/>
              <circle cx="18" cy="5.5" r="1" fill="currentColor" stroke="none"/>
              <circle cx="18" cy="12.5" r="1" fill="currentColor" stroke="none"/>
              <circle cx="18" cy="19.5" r="1" fill="currentColor" stroke="none"/>
            </svg>
            <span class="nav-label">服务器列表</span>
          </router-link>

          <router-link class="nav-item" to="/messages" active-class="active">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <span class="nav-label">消息中心</span>
          </router-link>

          <div v-if="isPlatformAdmin" class="nav-group">
            <div class="nav-group-header" @click="platformGroupOpen = !platformGroupOpen">
              <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 3l7 4v5c0 5-3.5 8-7 9-3.5-1-7-4-7-9V7l7-4z"/>
                <path d="M9.5 12l1.5 1.5 3.5-3.5"/>
              </svg>
              <span class="nav-label nav-label-group">
                平台管理
                <svg class="group-arrow" :class="{ open: platformGroupOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </span>
            </div>
            <div v-show="platformGroupOpen && sidebarOpen" class="nav-group-body">
              <router-link class="nav-item nav-item-sub" to="/platform-admin" active-class="active" exact>
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="3" width="7" height="7" rx="1"/>
                  <rect x="14" y="3" width="7" height="7" rx="1"/>
                  <rect x="3" y="14" width="7" height="7" rx="1"/>
                  <rect x="14" y="14" width="7" height="7" rx="1"/>
                </svg>
                <span class="nav-label">平台总览</span>
              </router-link>
              <router-link class="nav-item nav-item-sub" to="/platform-admin/servers" active-class="active">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="2" y="4" width="20" height="5" rx="1"/>
                  <rect x="2" y="10" width="20" height="5" rx="1"/>
                  <rect x="2" y="16" width="20" height="5" rx="1"/>
                </svg>
                <span class="nav-label">服务器管理</span>
              </router-link>
              <router-link class="nav-item nav-item-sub" to="/platform-admin/accounts" active-class="active">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="8" r="4"/>
                  <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
                  <line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/>
                </svg>
                <span class="nav-label">账号管理</span>
              </router-link>
              <router-link class="nav-item nav-item-sub" to="/platform-admin/cloud-blacklist" active-class="active">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/>
                  <path d="m9 12 2 2 4-4"/>
                </svg>
                <span class="nav-label">云黑审核</span>
              </router-link>
              <router-link class="nav-item nav-item-sub" to="/platform-admin/settings" active-class="active">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="3"/>
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.01a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                </svg>
                <span class="nav-label">平台设置</span>
              </router-link>
              <router-link class="nav-item nav-item-sub" to="/platform-admin/rbac" active-class="active">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                  <circle cx="9" cy="7" r="4"/>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                  <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
                <span class="nav-label">平台权限组</span>
              </router-link>
              <router-link class="nav-item nav-item-sub" to="/platform-admin/announcements" active-class="active">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
                  <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
                </svg>
                <span class="nav-label">公告管理</span>
              </router-link>
            </div>
          </div>

          <!-- 有服务器才显示以下内容 -->
          <template v-if="hasServers">
            <!-- 当前服务器选择器 -->
            <div class="server-section-header" v-if="sidebarOpen">当前服务器</div>
            <div class="server-picker" v-if="sidebarOpen">
              <select v-model="activeServerKey" class="server-picker-select" @change="onServerChange">
                <option v-for="s in myServers" :key="s.agent_key" :value="s.agent_key">
                  {{ s.online ? '[在线]' : '[离线]' }} {{ s.name }}
                </option>
              </select>
            </div>
            <div v-else class="server-picker-dot" :title="activeServer?.name || ''"
                 :class="activeServer?.online ? 'dot-online' : 'dot-offline'"></div>

            <!-- 仪表盘 -->
            <router-link class="nav-item" to="/dashboard" active-class="active">
              <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7" rx="1"/>
                <rect x="14" y="3" width="7" height="7" rx="1"/>
                <rect x="3" y="14" width="7" height="7" rx="1"/>
                <rect x="14" y="14" width="7" height="7" rx="1"/>
              </svg>
              <span class="nav-label">仪表盘</span>
            </router-link>

            <!-- 我的角色（所有成员可用） -->
            <router-link class="nav-item" to="/my-characters" active-class="active">
              <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="8" r="4"/>
                <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
              </svg>
              <span class="nav-label">我的角色</span>
            </router-link>

            <!-- 以下按面板权限组各自控制可见 -->

              <!-- 面板功能管理 -->
              <router-link v-if="hasPerm('panel.features')" class="nav-item" to="/panel-features" active-class="active">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="3"/>
                  <path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07M8.46 8.46a5 5 0 0 0 0 7.07"/>
                </svg>
                <span class="nav-label">面板功能管理</span>
              </router-link>

              <!-- 面板权限组管理（仅服主可见） -->
              <router-link v-if="isServerOwner" class="nav-item" to="/panel-groups" active-class="active">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
                <span class="nav-label">面板权限组管理</span>
              </router-link>

              <!-- TShock管理（可展开分组） -->
              <div v-if="hasPerm('tshock.config')" class="nav-group">
                <div class="nav-group-header" @click="tshockGroupOpen = !tshockGroupOpen">
                  <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="3"/>
                    <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
                  </svg>
                  <span class="nav-label nav-label-group">
                    TShock管理
                    <svg class="group-arrow" :class="{ open: tshockGroupOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                      <polyline points="9 18 15 12 9 6"/>
                    </svg>
                  </span>
                </div>
                <div v-show="tshockGroupOpen && sidebarOpen" class="nav-group-body">
                  <router-link class="nav-item nav-item-sub" to="/tshock/startup" active-class="active">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
                    </svg>
                    <span class="nav-label">启动脚本设置</span>
                  </router-link>
                  <router-link class="nav-item nav-item-sub" to="/tshock/motd" active-class="active">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                    <span class="nav-label">欢迎消息设置</span>
                  </router-link>
                  <router-link class="nav-item nav-item-sub" to="/tshock/config" active-class="active">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                      <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
                      <polyline points="10 9 9 9 8 9"/>
                    </svg>
                    <span class="nav-label">TShock config设置</span>
                  </router-link>
                  <router-link class="nav-item nav-item-sub" to="/tshock/ssc" active-class="active">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="8" r="4"/>
                      <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
                      <path d="M19 8h2M21 11l2-3-2-3"/>
                    </svg>
                    <span class="nav-label">SSC设置</span>
                  </router-link>
                  <router-link class="nav-item nav-item-sub" to="/tshock/plugins" active-class="active">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"/>
                      <line x1="16" y1="8" x2="2" y2="22"/>
                      <line x1="17.5" y1="15" x2="9" y2="15"/>
                    </svg>
                    <span class="nav-label">插件设置</span>
                  </router-link>
                  <router-link class="nav-item nav-item-sub" to="/tshock/groups" active-class="active">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                      <circle cx="9" cy="7" r="4"/>
                      <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                      <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                    </svg>
                    <span class="nav-label">游戏权限组管理</span>
                  </router-link>
                  <router-link class="nav-item nav-item-sub" to="/tshock/bans" active-class="active">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="10"/>
                      <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
                    </svg>
                    <span class="nav-label">用户封禁管理</span>
                  </router-link>
                  <router-link class="nav-item nav-item-sub" to="/tshock/banlists" active-class="active">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="3" y="3" width="18" height="18" rx="2"/>
                      <line x1="9" y1="3" x2="9" y2="21"/>
                      <line x1="3" y1="9" x2="21" y2="9"/>
                      <line x1="3" y1="15" x2="21" y2="15"/>
                      <line x1="15" y1="3" x2="15" y2="21"/>
                    </svg>
                    <span class="nav-label">图格物品弹幕封禁管理</span>
                  </router-link>
                </div>
              </div>

              <!-- 用户管理 -->
              <router-link v-if="hasPerm('panel.users')" class="nav-item" to="/users" active-class="active">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                  <circle cx="9" cy="7" r="4"/>
                  <line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/>
                </svg>
                <span class="nav-label">用户管理</span>
              </router-link>

              <!-- 控制台 -->
              <router-link v-if="hasPerm('panel.console')" class="nav-item" to="/console" active-class="active">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="2" y="3" width="20" height="16" rx="2"/>
                  <polyline points="6 8 10 12 6 16"/>
                  <line x1="13" y1="16" x2="20" y2="16"/>
                </svg>
                <span class="nav-label">控制台</span>
              </router-link>

              <!-- 文件管理 -->
              <router-link v-if="hasPerm('panel.files')" class="nav-item" to="/files" active-class="active">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                </svg>
                <span class="nav-label">文件管理</span>
              </router-link>
          </template>

        </nav>
      </aside>

      <!-- 移动端侧边栏遮罩 -->
      <div v-if="isMobile && sidebarOpen" class="sidebar-overlay" @click="sidebarOpen = false"></div>

      <!-- 内容区 -->
      <main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" :key="route.fullPath + activeServerKey" v-bind="{ wsState, agentOnline }" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, provide, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getToken, getEmail, clearAuth } from '@/api/auth'
import { listServers } from '@/api/servers'
import { getPlatformMe } from '@/api/platform'

const router = useRouter()
const route = useRoute()
const email  = getEmail() || ''
const token  = getToken() || ''

const isMobile = ref(window.innerWidth < 768)
function onResize() { isMobile.value = window.innerWidth < 768 }
window.addEventListener('resize', onResize)
onUnmounted(() => window.removeEventListener('resize', onResize))

const sidebarOpen     = ref(!isMobile.value)
const tshockGroupOpen = ref(false)
const platformGroupOpen = ref(false)
const wsState         = ref('disconnected')
const isPlatformAdmin = ref(false)
const platformAdminChecked = ref(false)
// 按 agent_key 追踪在线状态，待 activeServerKey 包含该 key 时 agentOnline 才为 true
const onlineAgentKeys = ref(new Set())
const hasWsOnlineSnapshot = ref(false)

function normalizeAgentKey(v) {
  return String(v || '').trim()
}

function syncMyServerOnlineFromWs() {
  if (!hasWsOnlineSnapshot.value) return
  myServers.value = myServers.value.map(s => ({
    ...s,
    online: onlineAgentKeys.value.has(normalizeAgentKey(s.agent_key)),
  }))
}

const agentOnline = computed(() => {
  const key = normalizeAgentKey(activeServerKey.value)
  if (!key) return false
  if (onlineAgentKeys.value.has(key)) return true
  // WS 尚未给出首帧在线快照时，兜底使用 REST 初始在线状态，避免误判为离线。
  if (!hasWsOnlineSnapshot.value) return !!activeServer.value?.online
  return false
})

// ── 服务器列表 & 当前选中 ──────────────────────────────────────
const myServers      = ref([])
const activeServerKey = ref(localStorage.getItem('active_agent_key') || '')
const hasServers     = computed(() => myServers.value.length > 0)
const activeServer   = computed(() =>
  myServers.value.find(s => s.agent_key === activeServerKey.value) || null
)
const canManageActiveServer = computed(() => {
  const server = activeServer.value
  if (!server) return false
  const role = server.server_role
  if (role === 'owner' || role === 'web_staff') return true
  const g = server.panel_group_name
  return g === '服主' || g === '管理'
})

// 检查当前用户是否拥有指定面板权限（支持 * 和 tshock.* 等通配）
function hasPerm(perm) {
  const server = activeServer.value
  if (!server) return false
  if (server.server_role === 'owner') return true
  const perms = server.panel_permissions || []
  for (const p of perms) {
    if (p === '*' || p === perm) return true
    if (p.endsWith('.*')) {
      const prefix = p.slice(0, -2)
      if (perm === prefix || perm.startsWith(prefix + '.')) return true
    }
  }
  return false
}

// 是否是服主（仅服主可执行的操作，如面板权限组管理）
const isServerOwner = computed(() => {
  const server = activeServer.value
  if (!server) return false
  if (server.server_role === 'owner') return true
  return server.panel_group_name === '服主'
})

async function loadServers() {
  try {
    myServers.value = await listServers()
    if (hasWsOnlineSnapshot.value) syncMyServerOnlineFromWs()
    const keys = myServers.value.map(s => s.agent_key)
    if (myServers.value.length === 0) {
      // 已无服务器（解散/离开后），清除缓存
      activeServerKey.value = ''
      localStorage.removeItem('active_agent_key')
    } else if (!keys.includes(activeServerKey.value)) {
      // 原来选中的已不存在，自动切换到第一个
      activeServerKey.value = myServers.value[0].agent_key
      localStorage.setItem('active_agent_key', activeServerKey.value)
    }
  } catch(e) { /* 忽略，不影响其他功能 */ }
}

async function detectPlatformAdmin() {
  try {
    await getPlatformMe()
    isPlatformAdmin.value = true
  } catch {
    isPlatformAdmin.value = false
  } finally {
    platformAdminChecked.value = true
  }
}

function onServerChange() {
  localStorage.setItem('active_agent_key', activeServerKey.value)
}

// 向子页面注入服务器状态（ServersView 刷新后通知 Layout 重新加载）
provide('myServers', myServers)
provide('activeServer', activeServer)
provide('activeServerKey', activeServerKey)
provide('reloadServers', loadServers)
provide('canManageActiveServer', canManageActiveServer)
provide('isServerOwner', isServerOwner)
provide('hasPerm', hasPerm)
provide('isPlatformAdmin', isPlatformAdmin)

// ── WebSocket 连接（全局共享，由 Layout 维护）──
let ws         = null
let retryTimer = null

const statusText = computed(() => ({
  connecting:   '连接中…',
  connected:    '已连接',
  disconnected: '已断开',
})[wsState.value])

function normalizeWsBase(raw) {
  const v = String(raw || '').trim()
  if (!v) return ''

  // 已是 ws/wss
  if (v.startsWith('ws://') || v.startsWith('wss://')) {
    return v.replace(/\/+$/, '')
  }

  // 由 http/https 自动映射到 ws/wss
  if (v.startsWith('http://') || v.startsWith('https://')) {
    return v
      .replace(/^http:\/\//i, 'ws://')
      .replace(/^https:\/\//i, 'wss://')
      .replace(/\/+$/, '')
  }

  // 只给了 host:port 的情况
  const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${wsProto}://${v.replace(/^\/+/, '').replace(/\/+$/, '')}`
}

function getWsUrl() {
  const configuredWsBase = normalizeWsBase(import.meta.env.VITE_WS_BASE)

  // 若未单独配置 WS，则复用 API 基地址（例如 http://x.x.x.x:8000）自动换算为 ws://...
  const apiBase = normalizeWsBase(import.meta.env.VITE_API_BASE || import.meta.env.VITE_API_PROXY_TARGET)

  // 最后兜底使用当前站点 origin 对应的 ws/wss
  const fallbackBase = normalizeWsBase(window.location.origin)
  const base = configuredWsBase || apiBase || fallbackBase
  return `${base}/ws/web?token=${encodeURIComponent(token)}`
}

function initWs() {
  wsState.value = 'connecting'
  const wsUrl = getWsUrl()
  try {
    ws = new WebSocket(wsUrl)
  } catch (err) {
    console.error('[WS] 创建连接失败:', err)
    wsState.value = 'disconnected'
    retryTimer = setTimeout(initWs, 5000)
    return
  }

  ws.onopen  = () => {
    wsState.value = 'connected'
    console.log('[WS] 连接已建立:', wsUrl)
  }

  ws.onclose = (e) => {
    wsState.value = 'disconnected'
    hasWsOnlineSnapshot.value = false
    onlineAgentKeys.value = new Set()   // 所有 Agent 全部标记为离线
    console.log(`[WS] 连接关闭 (code: ${e.code}, reason: ${e.reason || 'N/A'})`)
    
    if (e.code === 4001) {
      clearAuth()
      router.push('/login')
      return
    }
    
    // 避免在某些致命错误下无限重连
    if (e.code >= 4000 && e.code < 5000 && e.code !== 4001) {
      console.error('[WS] 服务器拒绝连接，停止重连')
      return
    }
    
    retryTimer = setTimeout(initWs, 5000)
  }

  ws.onerror = (err) => {
    console.error('[WS] 连接错误:', err)
    wsState.value = 'disconnected'
  }

  ws.onmessage = (e) => {
    let pkt
    try {
      pkt = JSON.parse(e.data)
    } catch (err) {
      console.error('[WS] 消息解析失败:', err)
      return
    }

    // 处理服务器错误消息
    if (pkt.type === 'error') {
      console.error('[WS] 服务器错误:', pkt.msg)
      if (pkt.msg?.includes('未授权')) {
        clearAuth()
        router.push('/login')
      }
      return
    }

    // 按 agent_key 更新在线状态
    if (pkt.type === 'auth' && Array.isArray(pkt.payload?.online_agents)) {
      // Web 认证成功时，后端返回当前已在线的 Agent 列表
      onlineAgentKeys.value = new Set(pkt.payload.online_agents.map(normalizeAgentKey))
      hasWsOnlineSnapshot.value = true
      syncMyServerOnlineFromWs()
    } else if (pkt.type === 'agent_status' && pkt.payload?.agent_key) {
      // Agent 上线 / 下线实时通知
      const s = new Set(onlineAgentKeys.value)
      const key = normalizeAgentKey(pkt.payload.agent_key)
      if (pkt.payload.online) s.add(key)
      else s.delete(key)
      onlineAgentKeys.value = s
      if (hasWsOnlineSnapshot.value) syncMyServerOnlineFromWs()
    } else if (pkt.type === 'status' && pkt.metadata?.agent_key) {
      // Agent 定期心跳，确保该 key 为在线
      const s = new Set(onlineAgentKeys.value)
      s.add(normalizeAgentKey(pkt.metadata.agent_key))
      onlineAgentKeys.value = s
      if (hasWsOnlineSnapshot.value) syncMyServerOnlineFromWs()
    }

    // 将消息广播给子页面
    window.dispatchEvent(new CustomEvent('ws-message', { detail: pkt }))
  }
}

function handleLogout() {
  clearAuth(); ws?.close(); router.push('/login')
}

// 暴露给子组件发送消息
function sendWs(data) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.warn('[WS] 连接未就绪，无法发送消息')
    return false
  }
  try {
    ws.send(JSON.stringify(data))
    return true
  } catch (err) {
    console.error('[WS] 发送消息失败:', err)
    return false
  }
}

onUnmounted(() => {
  clearTimeout(retryTimer)
  if (ws) {
    try { ws.close(1000, 'Component unmounted') } catch (err) { console.error('[WS] 关闭连接失败:', err) }
  }
})

// 通过全局事件让子页面调用 layout 的 sendWs
window.__tshockSend = sendWs

onMounted(() => {
  initWs()
  loadServers()
  detectPlatformAdmin()
})
onUnmounted(() => {
  clearTimeout(retryTimer)
  ws?.close()
})

// 路由权限映射：访问该路由所需的面板权限
const ROUTE_PERM_MAP = {
  '/console':         'panel.console',
  '/files':           'panel.files',
  '/users':           'panel.users',
  '/panel-features':  'panel.features',
  '/platform-admin':  'platform.admin',
  '/tshock/startup':  'tshock.startup',
  '/tshock/motd':     'tshock.motd',
  '/tshock/config':   'tshock.config',
  '/tshock/ssc':      'tshock.ssc',
  '/tshock/plugins':  'tshock.plugins',
  '/tshock/groups':   'tshock.groups',
  '/tshock/bans':     'tshock.bans',
  '/tshock/banlists': 'tshock.banlists',
}

watch(
  [() => route.path, activeServer, isPlatformAdmin, platformAdminChecked],
  ([path, server, platformAdmin, checked]) => {
    if (path.startsWith('/platform-admin')) {
      platformGroupOpen.value = true
      if (!checked) return
      if (!platformAdmin) router.replace('/home')
      return
    }
    if (!server) return  // 尚未选择服务器，不跳转
    // 服主专属页面
    if (path === '/panel-groups') {
      if (!isServerOwner.value) router.replace('/dashboard')
      return
    }
    const requiredPerm = ROUTE_PERM_MAP[path]
    if (requiredPerm && !hasPerm(requiredPerm)) {
      router.replace('/dashboard')
    }
  },
  { immediate: true }
)

// 移动端路由切换后自动关闭侧边栏
watch(() => route.fullPath, () => {
  if (isMobile.value) sidebarOpen.value = false
})

// 窗口大小变化时，桌面端自动展开、移动端自动收起
watch(isMobile, (v) => {
  sidebarOpen.value = !v
})
</script>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f1f5f9;
  color: #0f172a;
}

/* ── 顶栏 ── */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  height: 52px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
  z-index: 100;
}
.topbar-left  { display: flex; align-items: center; gap: 10px; }
.topbar-right { display: flex; align-items: center; gap: 12px; }

.sidebar-toggle {
  width: 34px; height: 34px;
  display: flex; align-items: center; justify-content: center;
  background: transparent; border: none; border-radius: 6px;
  color: #94a3b8; cursor: pointer; transition: all .15s;
}
.sidebar-toggle:hover { background: #f1f5f9; color: #475569; }
.sidebar-toggle svg   { width: 18px; height: 18px; }

.logo-icon  { font-size: 20px; }
.site-title { font-size: 15px; font-weight: 700; color: #0f172a; letter-spacing: .5px; }

.status-dot {
  width: 8px; height: 8px; border-radius: 50%;
}
.status-dot.connected    { background: #22c55e; box-shadow: 0 0 6px #22c55e; }
.status-dot.connecting   { background: #f59e0b; animation: pulse 1s infinite; }
.status-dot.disconnected { background: #ef4444; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

.status-text { font-size: 13px; color: #94a3b8; }
.user-email  { font-size: 13px; color: #64748b; }

.logout-btn {
  padding: 5px 14px;
  background: transparent; border: 1px solid #e2e8f0;
  border-radius: 6px; color: #64748b; font-size: 13px;
  cursor: pointer; transition: all .15s;
}
.logout-btn:hover { background: #f1f5f9; color: #0f172a; }

/* ── 主体区域 ── */
.body-area {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ── 侧边栏 ── */
.sidebar {
  width: 220px;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width .2s ease;
  overflow: hidden;
}
.sidebar.collapsed {
  width: 56px;
}

.nav-list {
  padding: 10px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-gutter: stable;
}

.nav-section-title {
  font-size: 10px;
  font-weight: 700;
  color: #cbd5e1;
  letter-spacing: .08em;
  text-transform: uppercase;
  padding: 12px 10px 4px;
  white-space: nowrap;
  overflow: hidden;
}

.server-section-header {
  font-size: 10px;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: .08em;
  text-transform: uppercase;
  padding: 12px 10px 2px;
  white-space: nowrap;
  overflow: hidden;
}

/* ── TShock 分组 ── */
.nav-group { display: flex; flex-direction: column; gap: 1px; }

.nav-group-header {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  box-sizing: border-box;
  padding: 9px 10px;
  border-radius: 8px;
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all .15s;
  white-space: nowrap;
  overflow: hidden;
  user-select: none;
}
.nav-group-header:hover { background: #f1f5f9; color: #0f172a; }

.nav-label-group {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 1;
  overflow: hidden;
}

.group-arrow {
  width: 14px; height: 14px;
  flex-shrink: 0;
  transition: transform .2s ease;
}
.group-arrow.open { transform: rotate(90deg); }

.nav-group-body {
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow: hidden;
}

.nav-item-sub {
  padding-left: 28px !important;
  font-size: 13px !important;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  box-sizing: border-box;
  flex: 0 0 auto;
  padding: 9px 10px;
  border-radius: 8px;
  color: #64748b;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all .15s;
  white-space: nowrap;
  overflow: hidden;
}
.nav-item:hover:not(.disabled) { background: #f1f5f9; color: #0f172a; }
.nav-item.active { background: #eff6ff; color: #2563eb; }
.nav-item.disabled { opacity: .4; cursor: not-allowed; pointer-events: none; }

.nav-icon {
  width: 18px; height: 18px;
  flex-shrink: 0;
  stroke: currentColor;
}
.nav-label {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.badge-soon {
  font-size: 10px;
  padding: 1px 5px;
  background: #eff6ff;
  color: #3b82f6;
  border-radius: 4px;
  font-weight: 600;
  white-space: nowrap;
}

/* ── 服务器选择器 ── */
.server-picker {
  margin: 2px 2px 6px;
  padding: 6px 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}
.server-picker-label {
  font-size: 10px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: .06em;
  margin-bottom: 4px;
}
.server-picker-select {
  width: 100%;
  padding: 5px 6px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 12.5px;
  color: #374151;
  background: #fff;
  cursor: pointer;
  outline: none;
}
.server-picker-select:focus { border-color: #3b82f6; }

/* 折叠时显示在线/离线小圆点 */
.server-picker-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  margin: 6px auto 4px;
}
.server-picker-dot.dot-online  { background: #22c55e; }
.server-picker-dot.dot-offline { background: #ef4444; }

/* ── 内容区 ── */
.main-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  scrollbar-gutter: stable;
}

.main-content :deep(> *) {
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
}

/* ── 页面切换动画 ── */
.page-fade-enter-active, .page-fade-leave-active {
  transition: opacity .15s ease, transform .15s ease;
}
.page-fade-enter-from { opacity: 0; transform: translateY(6px); }
.page-fade-leave-to   { opacity: 0; transform: translateY(-4px); }

/* ── 移动端适配 ── */
@media (max-width: 768px) {
  .topbar {
    padding: 0 12px;
    height: 48px;
  }
  .topbar-left { gap: 6px; }
  .site-title { font-size: 13px; }
  .status-text { display: none; }
  .user-email {
    max-width: 90px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 11px;
  }
  .logout-btn { padding: 4px 10px; font-size: 12px; }

  .sidebar {
    position: fixed;
    top: 48px;
    left: 0;
    bottom: 0;
    z-index: 200;
    width: 260px;
    transform: translateX(-100%);
    transition: transform .25s ease;
    box-shadow: 4px 0 24px rgba(0,0,0,.15);
  }
  .sidebar:not(.collapsed) {
    transform: translateX(0);
  }
  .sidebar.collapsed {
    transform: translateX(-100%);
    width: 260px;
  }

  .sidebar-overlay {
    position: fixed;
    inset: 0;
    top: 48px;
    z-index: 199;
    background: rgba(15, 23, 42, .4);
    transition: opacity .25s ease;
  }

  .nav-item {
    padding: 10px 12px;
    font-size: 14px;
    border-radius: 8px;
  }
  .nav-item-sub {
    padding-left: 30px !important;
  }
  .nav-group-header {
    padding: 10px 12px;
  }

  .main-content {
    width: 100%;
  }
}
</style>
