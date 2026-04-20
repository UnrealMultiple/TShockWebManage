import { createRouter, createWebHashHistory } from 'vue-router'
import { getToken } from '@/api/auth'

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

router.beforeEach((to) => {
  const token = getToken()
  if (to.meta.requiresAuth && !token) return { name: 'Login' }
  if (to.meta.guest && token) return { name: 'Home' }
})

export default router
