<template>
  <nav class="pa-nav" aria-label="平台管理导航">
    <router-link class="pa-nav-link" to="/platform-admin" exact-active-class="active">平台总览</router-link>
    <router-link class="pa-nav-link" to="/platform-admin/servers" active-class="active">服务器管理</router-link>
    <router-link class="pa-nav-link" to="/platform-admin/accounts" active-class="active">账号管理</router-link>
    <router-link class="pa-nav-link" to="/platform-admin/cloud-blacklist" active-class="active">云黑审核</router-link>
    <router-link class="pa-nav-link" to="/platform-admin/settings" active-class="active">平台设置</router-link>
    <router-link class="pa-nav-link" to="/platform-admin/rbac" active-class="active">平台权限组</router-link>
    <router-link class="pa-nav-link" to="/platform-admin/announcements" active-class="active">公告管理</router-link>
  </nav>
</template>
