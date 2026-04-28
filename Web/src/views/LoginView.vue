<template>
  <div class="auth-page">
    <div class="auth-card">
      <!-- Logo -->
      <div class="logo">
        <img class="logo-icon-img" :src="logoIconUrl" alt="TShock Logo" @error="handleLogoError" />
        <h1>TShock 管理平台</h1>
        <p class="subtitle">登录以继续</p>
      </div>

      <!-- 表单 -->
      <form @submit.prevent="handleLogin">
        <div class="field">
          <label>QQ 号 / QQ 邮箱</label>
          <input
            v-model="form.email"
            type="text"
            placeholder="123456789 或 123456789@qq.com"
            autocomplete="username"
            :disabled="loading"
          />
        </div>

        <div class="field">
          <label>密码</label>
          <input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            autocomplete="current-password"
            :disabled="loading"
          />
        </div>

        <div v-if="error" class="alert alert-error">{{ error }}</div>

        <button type="submit" class="btn btn-primary" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>

      <p class="forgot-link">
        <router-link to="/forgot-password">忘记密码？</router-link>
      </p>

      <p class="switch-link">
        还没有账号？
        <router-link to="/register">立即注册</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { login, saveAuth, getBootstrapStatus } from '@/api/auth'
import { normalizeQqEmailInput, qqEmailInputError } from '@/utils/qqEmail'

const router = useRouter()
const form   = ref({ email: '', password: '' })
const loading = ref(false)
const error   = ref('')
const logoIconUrl = ref(`${import.meta.env.BASE_URL}resources/app.ico`)

function handleLogoError() {
  if (logoIconUrl.value.endsWith('/resources/app.ico')) {
    logoIconUrl.value = `${import.meta.env.BASE_URL}resources/app.svg`
  }
}

async function checkBootstrapRequired() {
  try {
    const status = await getBootstrapStatus()
    if (status.bootstrap_required) router.replace('/bootstrap-platform-admin')
  } catch {
    // 忽略，允许用户继续在登录页操作
  }
}

async function handleLogin() {
  error.value = ''
  if (!form.value.email || !form.value.password) {
    error.value = '请填写 QQ 号和密码'
    return
  }
  const email = normalizeQqEmailInput(form.value.email)
  if (!email) {
    error.value = qqEmailInputError()
    return
  }
  loading.value = true
  try {
    const res = await login(email, form.value.password)
    saveAuth(res.token, res.email)
    const bootstrap = await getBootstrapStatus()
    router.push(bootstrap.bootstrap_required ? '/bootstrap-platform-admin' : '/home')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(checkBootstrapRequired)
</script>

<style scoped>
@import './auth.css';

.forgot-link {
  text-align: right;
  font-size: 13px;
  margin-top: -4px;
  margin-bottom: 8px;
}
.forgot-link a { color: #94a3b8; text-decoration: none; }
.forgot-link a:hover { color: #2563eb; text-decoration: underline; }

.logo-icon-img {
  width: 48px;
  height: 48px;
  display: block;
  margin: 0 auto 8px;
  object-fit: contain;
}
</style>
