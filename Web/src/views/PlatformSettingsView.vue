<template>
  <div class="cfg-page">
    <PageHeader title="平台设置" subtitle="Platform">
      <template #meta>
        <span v-if="modified" class="cfg-modified-badge">● 未保存</span>
      </template>
      <template #actions>
        <button class="cfg-btn cfg-btn-outline" :disabled="loading" @click="loadAll">
          {{ loading ? '刷新中' : '刷新' }}
        </button>
        <button class="cfg-btn cfg-btn-primary" :disabled="saving || loading || !modified" @click="saveSettings">
          {{ saving ? '保存中' : '保存设置' }}
        </button>
      </template>
    </PageHeader>

    <div class="cfg-editor">
      <div v-if="toast.message" :class="['cfg-toast', toast.type === 'ok' ? 'cfg-toast-ok' : 'cfg-toast-err']">
        {{ toast.message }}
        <button class="cfg-toast-close" @click="clearToast">x</button>
      </div>

      <div class="platform-settings-nav">
        <PlatformNav />
      </div>

      <div v-if="loading" class="cfg-loading">
        <div class="cfg-spinner"></div>
        <span>正在读取平台设置</span>
      </div>

      <div v-else class="cfg-fields-panel">
        <div class="cfg-field-row">
          <div class="cfg-field-meta">
            <div class="cfg-field-key">新服务器需要人工审核才可公开</div>
          </div>
          <div class="cfg-field-input-wrap">
            <label class="cfg-switch">
              <input v-model="form.requireAuditBeforePublic" type="checkbox" />
              <span class="cfg-switch-track"><span class="cfg-switch-thumb"></span></span>
            </label>
          </div>
        </div>

        <div class="cfg-field-row">
          <div class="cfg-field-meta">
            <div class="cfg-field-key">新服务器需要人工审核才可上线</div>
          </div>
          <div class="cfg-field-input-wrap">
            <label class="cfg-switch">
              <input v-model="form.requireAuditBeforeOnline" type="checkbox" />
              <span class="cfg-switch-track"><span class="cfg-switch-thumb"></span></span>
            </label>
          </div>
        </div>

        <div class="cfg-field-row">
          <div class="cfg-field-meta">
            <div class="cfg-field-key">单个账号最多可创建服务器数量</div>
            <div class="cfg-field-desc">0 表示不限制</div>
          </div>
          <div class="cfg-field-input-wrap">
            <input
              v-model.number="form.maxServersPerUser"
              class="cfg-input cfg-input-num"
              type="number"
              min="0"
              step="1"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import PlatformNav from '@/components/PlatformNav.vue'
import PageHeader from '@/components/PageHeader.vue'
import { getPlatformSettings, updatePlatformSetting } from '@/api/platform'
import './platform-admin.css'

const SETTINGS = {
  requireAuditBeforePublic: 'platform.server.require_audit_before_public',
  requireAuditBeforeOnline: 'platform.server.require_audit_before_online',
  maxServersPerUser: 'platform.max_servers_per_user',
}

const loading = ref(false)
const saving = ref(false)
const toast = reactive({ message: '', type: 'ok' })
const baseline = ref(null)
const form = reactive({
  requireAuditBeforePublic: true,
  requireAuditBeforeOnline: true,
  maxServersPerUser: 3,
})
const modified = computed(() => {
  if (!baseline.value) return false
  return form.requireAuditBeforePublic !== baseline.value.requireAuditBeforePublic
    || form.requireAuditBeforeOnline !== baseline.value.requireAuditBeforeOnline
    || Number(form.maxServersPerUser) !== Number(baseline.value.maxServersPerUser)
})

function showToast(message, type = 'ok') {
  toast.message = message
  toast.type = type
}

function clearToast() {
  toast.message = ''
}

function asBool(value, fallback = true) {
  if (value === undefined || value === null || value === '') return fallback
  return ['1', 'true', 'yes', 'on'].includes(String(value).toLowerCase())
}

function snapshotForm() {
  baseline.value = {
    requireAuditBeforePublic: form.requireAuditBeforePublic,
    requireAuditBeforeOnline: form.requireAuditBeforeOnline,
    maxServersPerUser: form.maxServersPerUser,
  }
}

async function loadAll() {
  loading.value = true
  clearToast()
  try {
    const data = await getPlatformSettings()
    form.requireAuditBeforePublic = asBool(data[SETTINGS.requireAuditBeforePublic], true)
    form.requireAuditBeforeOnline = asBool(data[SETTINGS.requireAuditBeforeOnline], true)
    form.maxServersPerUser = Math.max(0, Number.parseInt(data[SETTINGS.maxServersPerUser] ?? '3', 10) || 0)
    snapshotForm()
  } catch (e) {
    showToast(e.message || '加载平台设置失败', 'err')
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  clearToast()
  const maxServers = Math.max(0, Number.parseInt(form.maxServersPerUser, 10) || 0)
  try {
    await Promise.all([
      updatePlatformSetting(SETTINGS.requireAuditBeforePublic, {
        value: String(Boolean(form.requireAuditBeforePublic)),
        description: '新服务器需要平台人工审核后才可公开展示',
      }),
      updatePlatformSetting(SETTINGS.requireAuditBeforeOnline, {
        value: String(Boolean(form.requireAuditBeforeOnline)),
        description: '新服务器需要平台人工审核后才可上线',
      }),
      updatePlatformSetting(SETTINGS.maxServersPerUser, {
        value: String(maxServers),
        description: '单个账号最多可创建服务器数量，0 表示不限制',
      }),
    ])
    form.maxServersPerUser = maxServers
    snapshotForm()
    showToast('平台设置已保存')
  } catch (e) {
    showToast(e.message || '保存平台设置失败', 'err')
  } finally {
    saving.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.cfg-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: #f8fafc;
}

.cfg-modified-badge {
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 12px;
}

.cfg-modified-badge {
  border: 1px solid #fde68a;
  background: #fef3c7;
  color: #d97706;
}

.cfg-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.cfg-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.cfg-btn-outline {
  border: 1px solid #d1d5db;
  background: #fff;
  color: #374151;
}

.cfg-btn-outline:hover:not(:disabled) {
  border-color: #9ca3af;
  background: #f9fafb;
}

.cfg-btn-primary {
  background: #3b82f6;
  color: #fff;
}

.cfg-btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.cfg-editor {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.platform-settings-nav {
  flex-shrink: 0;
  padding: 14px 24px 0;
}

.cfg-toast {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  margin: 12px 24px 0;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
}

.cfg-toast-ok {
  border: 1px solid #bbf7d0;
  background: #dcfce7;
  color: #166534;
}

.cfg-toast-err {
  border: 1px solid #fecaca;
  background: #fee2e2;
  color: #991b1b;
}

.cfg-toast-close {
  padding: 0 0 0 12px;
  border: none;
  background: none;
  color: inherit;
  opacity: 0.6;
  cursor: pointer;
  font-size: 14px;
}

.cfg-fields-panel {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cfg-field-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
}

.cfg-field-meta {
  flex: 1;
  min-width: 0;
}

.cfg-field-key {
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
}

.cfg-field-desc {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.cfg-field-input-wrap {
  width: 160px;
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
}

.cfg-input {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #fff;
  color: #0f172a;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.cfg-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.cfg-input-num {
  max-width: 140px;
}

.cfg-switch {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}

.cfg-switch input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
}

.cfg-switch-track {
  position: relative;
  width: 40px;
  height: 22px;
  border-radius: 11px;
  background: #e2e8f0;
  transition: background 0.2s;
}

.cfg-switch input:checked + .cfg-switch-track {
  background: #3b82f6;
}

.cfg-switch-thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.18);
  transition: transform 0.2s;
}

.cfg-switch input:checked + .cfg-switch-track .cfg-switch-thumb {
  transform: translateX(18px);
}

.cfg-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 12px;
  padding: 60px 24px;
  color: #64748b;
  font-size: 14px;
}

.cfg-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 720px) {
  .platform-settings-nav,
  .cfg-fields-panel {
    padding-left: 14px;
    padding-right: 14px;
  }

  .cfg-field-row {
    align-items: stretch;
    flex-direction: column;
  }

  .cfg-field-input-wrap {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
