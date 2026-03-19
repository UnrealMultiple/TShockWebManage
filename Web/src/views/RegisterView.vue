<template>
  <div class="auth-page">
    <div class="auth-card">
      <!-- Logo -->
      <div class="logo">
        <img class="logo-icon-img" :src="logoIconUrl" alt="TShock Logo" @error="handleLogoError" />
        <h1>TShock 管理平台</h1>
        <p class="subtitle">创建新账号</p>
      </div>

      <!-- 第一步：填写信息 + 发送验证码 -->
      <form v-if="step === 1" @submit.prevent="handleSendCode">
        <div class="field">
          <label>QQ 邮箱</label>
          <input
            v-model="form.email"
            type="email"
            placeholder="example@qq.com"
            autocomplete="username"
            :disabled="loading"
          />
          <span class="field-hint">仅支持 @qq.com</span>
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

        <div v-if="error" class="alert alert-error">{{ error }}</div>
        <div v-if="success" class="alert alert-success">{{ success }}</div>

        <button type="submit" class="btn btn-primary" :disabled="loading || countdown > 0">
          <span v-if="loading" class="spinner"></span>
          {{ countdown > 0 ? `重新发送 (${countdown}s)` : (loading ? '发送中...' : '发送验证码') }}
        </button>
      </form>

      <!-- 第二步：输入验证码 -->
      <form v-else @submit.prevent="handleRegister">
        <div class="code-tip">
          <span class="code-icon">📧</span>
          <p>验证码已发送至</p>
          <p class="code-email">{{ form.email }}</p>
          <p class="code-sub">5 分钟内有效</p>
        </div>

        <div class="field">
          <label>验证码</label>
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
          {{ loading ? '注册中...' : '完成注册' }}
        </button>

        <button type="button" class="btn btn-ghost" @click="step = 1; error = ''">
          ← 返回修改
        </button>
      </form>

      <p class="switch-link">
        已有账号？
        <router-link to="/login">立即登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { sendCode, register, saveAuth } from '@/api/auth'

const router  = useRouter()
const step    = ref(1)
const loading = ref(false)
const error   = ref('')
const success = ref('')
const countdown = ref(0)
const logoIconUrl = ref(`${import.meta.env.BASE_URL}resources/app.ico`)

const form = ref({ email: '', password: '', confirm: '', code: '' })

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

async function handleSendCode() {
  error.value = ''
  success.value = ''

  const qqRe = /^[a-zA-Z0-9._%+\-]+@qq\.com$/i
  if (!qqRe.test(form.value.email)) {
    error.value = '仅支持 @qq.com 邮箱'
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

  loading.value = true
  try {
    await sendCode(form.value.email, form.value.password)
    success.value = '验证码已发送，请查收邮件'
    startCountdown()
    step.value = 2
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  error.value = ''
  if (form.value.code.length !== 6) {
    error.value = '请输入 6 位验证码'
    return
  }
  loading.value = true
  try {
    const res = await register(form.value.email, form.value.password, form.value.code)
    saveAuth(res.token, res.email)
    router.push('/home')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
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
