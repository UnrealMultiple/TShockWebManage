<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="logo">
        <img class="logo-icon-img" :src="logoIconUrl" alt="TShock Logo" @error="handleLogoError" />
        <h1>平台超级管理初始化</h1>
        <p class="subtitle">当前平台还没有超级管理账号。请使用配置文件中的一次性 token 完成首次创建。</p>
      </div>

      <form v-if="step === 1" @submit.prevent="handleSendCode">
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
            placeholder="至少 8 位"
            autocomplete="new-password"
            :disabled="loading"
          />
        </div>

        <div class="field">
          <label>确认密码</label>
          <input
            v-model="form.confirm"
            type="password"
            placeholder="再次输入密码"
            autocomplete="new-password"
            :disabled="loading"
          />
        </div>

        <div class="field">
          <label>Bootstrap Token</label>
          <input
            v-model="form.bootstrapToken"
            type="password"
            placeholder="填写 server_config.json 中的平台初始化令牌"
            :disabled="loading"
          />
        </div>

        <div v-if="error" class="alert alert-error">{{ error }}</div>
        <div v-if="success" class="alert alert-success">{{ success }}</div>

        <button type="submit" class="btn btn-primary" :disabled="loading || countdown > 0">
          <span v-if="loading" class="spinner"></span>
          {{ countdown > 0 ? `重新发送 (${countdown}s)` : (loading ? '发送中...' : '发送验证码') }}
        </button>

        <p class="switch-link">
          已有账号？
          <router-link to="/login">返回登录</router-link>
        </p>
      </form>

      <form v-else @submit.prevent="handleBootstrapRegister">
        <div class="code-tip">
          <span class="code-icon">📧</span>
          <p>验证码已发送至</p>
          <p class="code-email">{{ form.email }}</p>
          <p class="code-sub">验证成功后会自动成为平台超级管理</p>
        </div>

        <div class="field">
          <label>邮箱验证码</label>
          <input
            v-model="form.code"
            type="text"
            placeholder="请输入 6 位验证码"
            maxlength="6"
            inputmode="numeric"
            autocomplete="one-time-code"
            :disabled="loading"
            class="code-input"
          />
        </div>

        <div v-if="error" class="alert alert-error">{{ error }}</div>

        <button type="submit" class="btn btn-primary" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '创建中...' : '创建超级管理账号' }}
        </button>

        <button type="button" class="btn btn-ghost" @click="step = 1; error = ''">
          ← 返回修改
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { bootstrapRegister, bootstrapSendCode, getBootstrapStatus, saveAuth } from '@/api/auth'
import { normalizeQqEmailInput, qqEmailInputError } from '@/utils/qqEmail'

const router = useRouter()
const step = ref(1)
const loading = ref(false)
const error = ref('')
const success = ref('')
const countdown = ref(0)
const logoIconUrl = ref(`${import.meta.env.BASE_URL}resources/app.ico`)
const form = ref({
  email: '',
  password: '',
  confirm: '',
  bootstrapToken: '',
  code: '',
})

let countdownTimer = null

function handleLogoError() {
  if (logoIconUrl.value.endsWith('/resources/app.ico')) {
    logoIconUrl.value = `${import.meta.env.BASE_URL}resources/app.svg`
  }
}

function startCountdown() {
  countdown.value = 60
  countdownTimer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) clearInterval(countdownTimer)
  }, 1000)
}

async function guardBootstrapStatus() {
  try {
    const status = await getBootstrapStatus()
    if (!status.bootstrap_required) {
      router.replace('/login')
    }
  } catch {
    // 忽略，保留页面让用户稍后重试
  }
}

async function handleSendCode() {
  error.value = ''
  success.value = ''

  const email = normalizeQqEmailInput(form.value.email)
  if (!email) {
    error.value = qqEmailInputError()
    return
  }
  if (form.value.password.length < 8) {
    error.value = '密码至少需要 8 位'
    return
  }
  if (form.value.password !== form.value.confirm) {
    error.value = '两次输入的密码不一致'
    return
  }
  if (!form.value.bootstrapToken.trim()) {
    error.value = '请输入 bootstrap token'
    return
  }

  loading.value = true
  try {
    form.value.email = email
    await bootstrapSendCode(email, form.value.password, form.value.bootstrapToken.trim())
    success.value = '验证码已发送，请查收邮件'
    startCountdown()
    step.value = 2
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function handleBootstrapRegister() {
  error.value = ''
  if (form.value.code.length !== 6) {
    error.value = '请输入 6 位验证码'
    return
  }
  const email = normalizeQqEmailInput(form.value.email)
  if (!email) {
    error.value = qqEmailInputError()
    return
  }
  loading.value = true
  try {
    const res = await bootstrapRegister(
      email,
      form.value.password,
      form.value.code,
      form.value.bootstrapToken.trim(),
    )
    saveAuth(res.token, res.email)
    router.replace('/home')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(guardBootstrapStatus)
</script>

<style scoped>
@import './auth.css';

.code-tip {
  text-align: center;
  padding: 20px 0 12px;
  color: #94a3b8;
  font-size: 14px;
}

.code-icon { font-size: 40px; display: block; margin-bottom: 8px; }
.code-email { color: #60a5fa; font-weight: 600; margin: 4px 0; }
.code-sub { font-size: 12px; color: #475569; }
.code-input {
  text-align: center;
  font-size: 24px;
  letter-spacing: 8px;
  font-weight: bold;
}

.logo-icon-img {
  width: 48px;
  height: 48px;
  display: block;
  margin: 0 auto 8px;
  object-fit: contain;
}
</style>
