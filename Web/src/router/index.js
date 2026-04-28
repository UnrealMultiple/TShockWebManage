import { createRouter, createWebHashHistory } from 'vue-router'
import { clearAuth, getCurrentUser, getToken } from '@/api/auth'

const routes = [
  {
    path: '/',
    redirect: '/home'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { guest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { guest: true }
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/ForgotPasswordView.vue'),
  },
  {
    path: '/bootstrap-platform-admin',
    name: 'BootstrapPlatformAdmin',
    component: () => import('@/views/BootstrapPlatformAdminView.vue'),
    meta: { guest: true }
  },
  {
    // 主布局（含侧边栏+顶栏）
    path: '/',
    component: () => import('@/views/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: 'home',
        name: 'Home',
        component: () => import('@/views/HomeView.vue'),
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/DashboardView.vue'),
      },
      {
        path: 'console',
        name: 'Console',
        component: () => import('@/views/ConsoleView.vue'),
      },
      {
        path: 'files',
        name: 'Files',
        component: () => import('@/views/FilesView.vue'),
      },
      {
        path: 'servers',
        name: 'Servers',
        component: () => import('@/views/ServersView.vue'),
      },
      {
        path: 'messages',
        name: 'Messages',
        component: () => import('@/views/MessagesView.vue'),
      },
      {
        path: 'platform-admin',
        name: 'PlatformAdmin',
        component: () => import('@/views/PlatformAdminView.vue'),
        meta: { title: '平台总览' }
      },
      {
        path: 'platform-admin/servers',
        name: 'PlatformServers',
        component: () => import('@/views/PlatformServersView.vue'),
        meta: { title: '服务器管理' }
      },
      {
        path: 'platform-admin/accounts',
        name: 'PlatformAccounts',
        component: () => import('@/views/PlatformAccountsView.vue'),
        meta: { title: '账号管理' }
      },
      {
        path: 'platform-admin/cloud-blacklist',
        name: 'PlatformCloudBlacklist',
        component: () => import('@/views/PlatformCloudBlacklistView.vue'),
        meta: { title: '云黑审核' }
      },
      {
        path: 'platform-admin/settings',
        name: 'PlatformSettings',
        component: () => import('@/views/PlatformSettingsView.vue'),
        meta: { title: '平台设置' }
      },
      {
        path: 'platform-admin/rbac',
        name: 'PlatformRbac',
        component: () => import('@/views/PlatformRbacView.vue'),
        meta: { title: '平台权限组' }
      },
      {
        path: 'platform-admin/announcements',
        name: 'PlatformAnnouncements',
        component: () => import('@/views/PlatformAnnouncementsView.vue'),
        meta: { title: '公告管理' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/UserManagementView.vue'),
      },
      {
        path: 'my-characters',
        name: 'MyCharacters',
        component: () => import('@/views/MyCharactersView.vue'),
      },
      // ── 面板管理 ──
      {
        path: 'panel-features',
        name: 'PanelFeatures',
        component: () => import('@/views/PanelFeaturesView.vue'),
        meta: { title: '面板功能管理' }
      },
      {
        path: 'panel-groups',
        name: 'PanelGroups',
        component: () => import('@/views/PanelGroupsView.vue'),
        meta: { title: '面板权限组管理' }
      },
      // ── TShock管理 ──
      {
        path: 'tshock/startup',
        name: 'TShockStartup',
        component: () => import('@/views/StartupScriptView.vue'),
        meta: { title: '启动脚本设置' }
      },
      {
        path: 'tshock/motd',
        name: 'TShockMotd',
        component: () => import('@/views/MotdView.vue'),
        meta: { title: '欢迎消息设置' }
      },
      {
        path: 'tshock/config',
        name: 'TShockConfig',
        component: () => import('@/views/TShockConfigView.vue'),
        props: { configFile: 'config' },
        meta: { title: 'TShock config设置' }
      },
      {
        path: 'tshock/ssc',
        name: 'TShockSSC',
        component: () => import('@/views/TShockConfigView.vue'),
        props: { configFile: 'ssc' },
        meta: { title: 'SSC设置' }
      },
      {
        path: 'tshock/plugins',
        name: 'TShockPlugins',
        component: () => import('@/views/PluginsView.vue'),
        meta: { title: '插件管理' }
      },
      {
        path: 'tshock/groups',
        name: 'TShockGroups',
        component: () => import('@/views/GameGroupsView.vue'),
        meta: { title: '游戏权限组管理' }
      },
      {
        path: 'tshock/bans',
        name: 'TShockBans',
        component: () => import('@/views/BansView.vue'),
        meta: { title: '用户封禁管理' }
      },
      {
        path: 'tshock/banlists',
        name: 'TShockBanlists',
        component: () => import('@/views/BanlistsView.vue'),
        meta: { title: '图格物品弹幕封禁管理' }
      },
    ]
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

let authCheckPromise = null

async function validateToken() {
  const token = getToken()
  if (!token) return false
  if (!authCheckPromise) {
    authCheckPromise = getCurrentUser()
      .then(() => true)
      .catch((err) => {
        if (err?.status === 401 || err?.status === 403) {
          clearAuth()
          return false
        }
        console.warn('[Auth] 跳过本次登录态校验失败:', err?.message || err)
        return true
      })
      .finally(() => {
        authCheckPromise = null
      })
  }
  return authCheckPromise
}

router.beforeEach(async (to) => {
  const token = getToken()
  if (to.meta.requiresAuth) {
    if (!token) return { name: 'Login' }
    const valid = await validateToken()
    if (!valid) return { name: 'Login' }
  }
  if (to.meta.guest && token) {
    const valid = await validateToken()
    if (valid) return { name: 'Home' }
  }
})

export default router
