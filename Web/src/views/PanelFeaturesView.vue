<template>
  <div class="cfg-page">
    <div class="cfg-header">
      <div class="cfg-header-left">
        <h2 class="cfg-title">面板功能管理</h2>
        <span class="cfg-subtitle">panel_features.json</span>
        <span v-if="hasChanges" class="cfg-modified-badge">● 未保存</span>
      </div>
      <div class="cfg-header-right">
        <button class="cfg-btn cfg-btn-outline" @click="loadSettings" :disabled="loading || !activeServer">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
          </svg>
          刷新
        </button>
        <button class="cfg-btn cfg-btn-primary" @click="saveSettings" :disabled="saving || !hasChanges || !canManage || !activeServer">
          <svg v-if="saving" viewBox="0 0 24 24" class="spinning" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
          {{ saving ? '保存中…' : '保存配置' }}
        </button>
      </div>
    </div>

    <div v-if="!activeServer" class="cfg-empty">
      <div class="cfg-empty-icon">⚙️</div>
      <p>请先在左侧选择一个服务器</p>
    </div>

    <template v-else>
      <div v-if="loading" class="cfg-loading">
        <div class="cfg-spinner"></div>
        <span>正在加载配置…</span>
      </div>

      <div v-else class="cfg-editor">
        <div v-if="errorMsg" class="cfg-toast cfg-toast-err">
          {{ errorMsg }}
          <button class="cfg-toast-close" @click="errorMsg = ''">✕</button>
        </div>
        <div v-if="okMsg" class="cfg-toast cfg-toast-ok">
          {{ okMsg }}
          <button class="cfg-toast-close" @click="okMsg = ''">✕</button>
        </div>

        <div class="cfg-fields-panel">
          <div class="cfg-field-row">
            <div class="cfg-field-meta">
              <div class="cfg-field-key">每个账户最大注册角色数量</div>
              <div class="cfg-field-desc">限制单个面板账号可绑定的游戏角色数量，0 表示禁止创建新角色。</div>
            </div>
            <div class="cfg-field-input-wrap">
              <input
                v-model.number="form.register_limit"
                type="number"
                min="0"
                max="50"
                class="cfg-input"
                :disabled="saving || !canManage"
              />
            </div>
          </div>
        </div>

        <p v-if="!canManage" class="cfg-note">当前账号无权限修改此配置。</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, inject, ref, watch } from 'vue'
import { getPanelFeatures, updatePanelFeatures } from '@/api/servers'

const activeServer = inject('activeServer', ref(null))
const canManage = inject('canManageActiveServer', ref(false))

const loading = ref(false)
const saving = ref(false)
const errorMsg = ref('')
const okMsg = ref('')

const form = ref({ register_limit: 1 })
const originalLimit = ref(1)

const hasChanges = computed(() => Number(form.value.register_limit) !== Number(originalLimit.value))

function normalizeLimit(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return 1
  return Math.max(0, Math.min(50, Math.round(n)))
}

watch(() => form.value.register_limit, (v) => {
  const normalized = normalizeLimit(v)
  if (normalized !== v) form.value.register_limit = normalized
})

async function loadSettings() {
  const sid = activeServer.value?.id
  if (!sid) return
  loading.value = true
  errorMsg.value = ''
  okMsg.value = ''
  try {
    const data = await getPanelFeatures(sid)
    const limit = normalizeLimit(data.register_limit)
    originalLimit.value = limit
    form.value.register_limit = limit
  } catch (e) {
    errorMsg.value = e.message || '加载配置失败'
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  const sid = activeServer.value?.id
  if (!sid || !canManage.value) return
  saving.value = true
  errorMsg.value = ''
  okMsg.value = ''
  try {
    const payload = { register_limit: normalizeLimit(form.value.register_limit) }
    const data = await updatePanelFeatures(sid, payload)
    const limit = normalizeLimit(data.register_limit)
    originalLimit.value = limit
    form.value.register_limit = limit
    okMsg.value = '配置已保存'
  } catch (e) {
    errorMsg.value = e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

watch(() => activeServer.value?.id, (id) => {
  if (id) loadSettings()
  else {
    form.value.register_limit = 1
    originalLimit.value = 1
    errorMsg.value = ''
    okMsg.value = ''
  }
}, { immediate: true })
</script>

<style scoped>
/* 与 TShock 主配置页保持一致的基础布局 */
.cfg-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: #f8fafc;
}

.cfg-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 28px 16px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
  gap: 12px;
  flex-wrap: wrap;
}

.cfg-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.cfg-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cfg-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.cfg-subtitle {
  font-size: 12px;
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  padding: 2px 8px;
  border-radius: 20px;
  font-family: monospace;
}

.cfg-modified-badge {
  font-size: 12px;
  color: #d97706;
  background: #fef3c7;
  border: 1px solid #fde68a;
  border-radius: 20px;
  padding: 2px 8px;
  animation: pulse-dot 1.5s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: .5; }
}

.cfg-editor {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.cfg-fields-panel {
  padding: 12px 24px 24px;
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
  min-width: 0;
  flex: 1;
}

.cfg-field-key {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.cfg-field-desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.45;
  color: #64748b;
}

.cfg-field-input-wrap {
  width: 140px;
  flex-shrink: 0;
}

.cfg-input {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 13px;
  color: #0f172a;
  background: #fff;
  outline: none;
  transition: border-color 0.15s;
}

.cfg-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,.12);
}

.cfg-note {
  margin: 0 24px 20px;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fcd34d;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
}

.cfg-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  text-align: center;
  color: #94a3b8;
  padding: 60px 24px;
  font-size: 14px;
}

.cfg-empty-icon {
  font-size: 40px;
}

.cfg-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 12px;
  padding: 60px 24px;
  font-size: 14px;
  color: #64748b;
}

.cfg-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin .7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.cfg-toast {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 12px 24px 0;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  flex-shrink: 0;
}

.cfg-toast-ok {
  background: #dcfce7;
  border: 1px solid #bbf7d0;
  color: #166534;
}

.cfg-toast-err {
  background: #fee2e2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.cfg-toast-close {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 14px;
  opacity: .6;
  padding: 0 0 0 12px;
}

.cfg-toast-close:hover {
  opacity: 1;
}

.cfg-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
}

.cfg-btn svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.cfg-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.cfg-btn-primary {
  background: #3b82f6;
  color: #fff;
}

.cfg-btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.cfg-btn-outline {
  background: #fff;
  border: 1px solid #d1d5db;
  color: #374151;
}

.cfg-btn-outline:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #9ca3af;
}

.spinning {
  animation: spin .7s linear infinite;
}

@media (max-width: 768px) {
  .cfg-header {
    padding: 18px 14px 14px;
  }

  .cfg-fields-panel {
    padding: 10px 14px 16px;
  }

  .cfg-toast {
    margin: 10px 14px 0;
  }

  .cfg-note {
    margin: 0 14px 16px;
  }

  .cfg-field-row {
    flex-direction: column;
    align-items: stretch;
  }

  .cfg-field-input-wrap {
    width: 100%;
  }
}
</style>
