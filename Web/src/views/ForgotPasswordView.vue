<template>
  <div class="auth-page">
    <div class="auth-card">
      <!-- Logo -->
      <div class="logo">
        <div class="logo-icon-wrap">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
        </div>
        <h1>重置密码</h1>
        <p class="subtitle">{{ step === 1 ? '输入 QQ 号以接收验证码' : '验证身份并设置新密码' }}</p>
      </div>

      <!-- 第一步：输入邮箱 -->
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

        <div v-if="error"   class="alert alert-error">{{ error }}</div>
        <div v-if="success" class="alert alert-success">{{ success }}</div>

        <button type="submit" class="btn btn-primary" :disabled="loading || countdown > 0">
          <span v-if="loading" class="spinner"></span>
          {{ countdown > 0 ? `重新发送 (${countdown}s)` : (loading ? '发送中...' : '发送验证码') }}
        </button>
      </form>

      <!-- 第二步：验证码 + 新密码 -->
      <form v-else @submit.prevent="handleReset">
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

        <div class="field">
          <label>新密码</label>
          <input
            v-model="form.password"
            type="password"
            placeholder="至少 8 位"
            autocomplete="new-password"
            :disabled="loading"
          />
        </div>

        <div class="field">
          <label>确认新密码</label>
          <input
            v-model="form.confirm"
            type="password"
            placeholder="再次输入新密码"
            autocomplete="new-password"
            :disabled="loading"
          />
        </div>

        <div v-if="error"   class="alert alert-error">{{ error }}</div>
        <div v-if="success" class="alert alert-success">{{ success }}</div>

        <button type="submit" class="btn btn-primary" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '重置中...' : '确认重置' }}
        </button>

        <button type="button" class="btn btn-ghost" @click="step = 1; error = ''">
          ← 返回
        </button>
      </form>

      <p class="switch-link">
        想起密码了？
        <router-link to="/login">返回登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { resetSendCode, resetConfirm } from '@/api/auth'
import { normalizeQqEmailInput, qqEmailInputError } from '@/utils/qqEmail'

const router  = useRouter()
const step    = ref(1)
const loading = ref(false)
const error   = ref('')
const success = ref('')
const countdown = ref(0)

const form = ref({ email: '', code: '', password: '', confirm: '' })

let countdownTimer = null

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
  const email = normalizeQqEmailInput(form.value.email)
  if (!email) { error.value = qqEmailInputError(); return }

  loading.value = true
  try {
    form.value.email = email
    await resetSendCode(email)
    success.value = '验证码已发送，请查收邮件'
    startCountdown()
    step.value = 2
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function handleReset() {
  error.value = ''
  if (form.value.code.length !== 6) { error.value = '请输入 6 位验证码'; return }
  const email = normalizeQqEmailInput(form.value.email)
  if (!email) { error.value = qqEmailInputError(); return }
  if (form.value.password.length < 8) { error.value = '新密码至少需要 8 位'; return }
  if (form.value.password !== form.value.confirm) { error.value = '两次输入的密码不一致'; return }

  loading.value = true
  try {
    await resetConfirm(email, form.value.code, form.value.password)
    success.value = '密码重置成功，即将跳转登录…'
    setTimeout(() => router.push('/login'), 1500)
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
.code-email { color: #2563eb; font-weight: 600; margin: 4px 0; }
.code-sub { font-size: 12px; color: #94a3b8; }
.code-input {
  text-align: center;
  font-size: 24px;
  letter-spacing: 8px;
  font-weight: bold;
}
</style>
