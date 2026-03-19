<template>
  <div class="cfg-page">
    <!-- ── 顶部标题栏 ── -->
    <div class="cfg-header">
      <div class="cfg-header-left">
        <h2 class="cfg-title">{{ fileConf.title }}</h2>
        <span class="cfg-subtitle">{{ fileConf.subtitle }}</span>
        <span v-if="modified" class="cfg-modified-badge">● 未保存</span>
      </div>
      <div class="cfg-header-right">
        <button class="cfg-btn cfg-btn-outline" @click="loadConfig" :disabled="loading || !agentOnline || !activeServerKey">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
          </svg>
          刷新
        </button>
        <button class="cfg-btn cfg-btn-outline" @click="doReload"
          :disabled="!agentOnline || !activeServerKey || reloading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 1 1-.49-3.18"/>
          </svg>
          {{ reloading ? '重载中…' : '立即重载' }}
        </button>
        <button class="cfg-btn cfg-btn-primary" @click="saveConfig"
          :disabled="!modified || saving || !agentOnline || !activeServerKey">
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

    <!-- Agent 离线提示 -->
    <div v-if="!agentOnline" class="cfg-offline">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <span>Agent 未连接，无法读取或保存配置。请先启动服务器。</span>
    </div>

    <template v-else>
      <!-- 加载中 -->
      <div v-if="loading" class="cfg-loading">
        <div class="cfg-spinner"></div>
        <span>正在从服务器读取配置…</span>
      </div>

      <!-- 错误 -->
      <div v-else-if="loadError" class="cfg-error">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <div>
          <strong>读取失败</strong>
          <p>{{ loadError }}</p>
          <button class="cfg-btn cfg-btn-outline" style="margin-top:8px" @click="loadConfig">重试</button>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="!configLoaded" class="cfg-empty">
        <div class="cfg-empty-icon">⚙️</div>
        <p>点击刷新按钮读取服务器配置文件</p>
        <button class="cfg-btn cfg-btn-primary" @click="loadConfig">读取配置</button>
      </div>

      <!-- 配置编辑器 -->
      <div v-else class="cfg-editor">
        <!-- 操作结果提示 -->
        <div v-if="saveResult" :class="['cfg-toast', saveResult.ok ? 'cfg-toast-ok' : 'cfg-toast-err']">
          {{ saveResult.msg }}
          <button class="cfg-toast-close" @click="saveResult = null">✕</button>
        </div>

        <!-- 搜索框 -->
        <div class="cfg-search-bar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input v-model="searchQuery" class="cfg-search-input" placeholder="搜索配置项…" />
          <button v-if="searchQuery" class="cfg-search-clear" @click="searchQuery = ''">✕</button>
        </div>

        <!-- 搜索模式：扁平列表 -->
        <div v-if="searchQuery.trim()" class="cfg-search-results">
          <div v-if="filteredFields.length === 0" class="cfg-no-result">没有匹配"{{ searchQuery }}"的配置项</div>
          <template v-else>
            <div v-for="f in filteredFields" :key="f.key" class="cfg-field-row">
              <FieldControl :field="f" :modelValue="configData[f.key]"
                @update:modelValue="setField(f.key, $event)" />
            </div>
          </template>
        </div>

        <!-- 分类标签页 -->
        <template v-else>
          <div class="cfg-cats">
            <button v-for="cat in categories" :key="cat"
              :class="['cfg-cat-btn', { active: activeCat === cat }]"
              @click="activeCat = cat">
              {{ cat }}
              <span class="cfg-cat-count">{{ countByCategory[cat] }}</span>
            </button>
          </div>

          <div class="cfg-fields-panel">
            <div v-for="f in currentFields" :key="f.key" class="cfg-field-row">
              <FieldControl :field="f" :modelValue="configData[f.key]"
                @update:modelValue="setField(f.key, $event)" />
            </div>
          </div>
        </template>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, inject } from 'vue'
import { CONFIG_FILE_MAP } from '@/config/tshock_schema.js'
import FieldControl from '@/components/config/FieldControl.vue'

const props = defineProps({
  configFile:  { type: String,  default: 'config' },
  agentOnline: { type: Boolean, default: false },
})

const activeServer    = inject('activeServer',    ref(null))
const activeServerKey = inject('activeServerKey', ref(''))

// ── 状态 ─────────────────────────────────────────────────────────────
const loading      = ref(false)
const saving       = ref(false)
const reloading    = ref(false)
const loadError    = ref('')
const configLoaded = ref(false)
const modified     = ref(false)
const saveResult   = ref(null)
const activeCat    = ref('')
const searchQuery  = ref('')
const configData   = ref({})
const rawWrapper   = ref(null)

const fileConf = computed(() => CONFIG_FILE_MAP[props.configFile] || CONFIG_FILE_MAP.config)
const schema   = computed(() => fileConf.value.schema)

// schema 快速查找表：key → 字段定义
const schemaMap = computed(() => {
  const m = {}
  for (const f of schema.value) m[f.key] = f
  return m
})

// ── 类型自动推断（用于不在 schema 中的字段） ─────────────────────────
function detectType(val) {
  if (typeof val === 'boolean') return 'boolean'
  if (typeof val === 'number')  return 'number'
  if (Array.isArray(val))       return 'json'
  if (val !== null && typeof val === 'object') return 'json'
  return 'string'
}

const ALL_CAT     = '全部'
const UNKNOWN_CAT = '其他'

// ── 以实际文件内容为准，生成字段定义列表 ────────────────────────────
// · 文件中存在 且 schema 有定义 → 使用 schema 的 type/category/description
// · 文件中存在 但 schema 无定义 → 自动推断类型，归入"其他"
// · schema 有定义 但文件中不存在 → 完全不出现（不补默认值、不写入）
const effectiveFields = computed(() =>
  Object.keys(configData.value).map(key => {
    const s = schemaMap.value[key]
    if (s) return s
    return {
      key,
      type:        detectType(configData.value[key]),
      category:    UNKNOWN_CAT,
      description: '当前 TShock 版本特有字段（不在内置 schema 中）',
    }
  })
)

// ── 类别与字段（基于 effectiveFields，而非静态 schema） ───────────────
const categories = computed(() => {
  const seen = [ALL_CAT]
  for (const f of effectiveFields.value) {
    if (!seen.includes(f.category)) seen.push(f.category)
  }
  return seen
})

const countByCategory = computed(() => {
  const m = { [ALL_CAT]: effectiveFields.value.length }
  for (const f of effectiveFields.value) m[f.category] = (m[f.category] || 0) + 1
  return m
})

const currentFields = computed(() =>
  activeCat.value === ALL_CAT
    ? effectiveFields.value
    : effectiveFields.value.filter(f => f.category === activeCat.value)
)

const filteredFields = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return []
  return effectiveFields.value.filter(f =>
    f.key.toLowerCase().includes(q) || (f.description || '').toLowerCase().includes(q)
  )
})

// ── 加载配置 ─────────────────────────────────────────────────────────
function loadConfig() {
  if (!activeServerKey.value) return
  loading.value   = true
  loadError.value = ''
  window.__tshockSend?.({
    type: 'read_tshock_config',
    msg_id: `cfg-read-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, file: props.configFile },
  })
}

// ── 保存配置 ─────────────────────────────────────────────────────────
function saveConfig() {
  if (!modified.value || !activeServerKey.value) return
  saving.value = true

  // 清理 rest_tokens 字段中 key 为空string 的临时行
  const cleaned = { ...configData.value }
  for (const key of Object.keys(cleaned)) {
    const f = schemaMap.value[key]
    if (f?.type === 'rest_tokens' && cleaned[key] && typeof cleaned[key] === 'object' && !Array.isArray(cleaned[key])) {
      const filtered = {}
      for (const [k, v] of Object.entries(cleaned[key])) {
        if (k) filtered[k] = v
      }
      cleaned[key] = filtered
    }
  }

  // 若原始文件有 Settings 包装器，写回时保留该结构
  const toWrite = rawWrapper.value
    ? { ...rawWrapper.value, Settings: cleaned }
    : cleaned
  const content = JSON.stringify(toWrite, null, 2)
  window.__tshockSend?.({
    type: 'write_tshock_config',
    msg_id: `cfg-write-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, file: props.configFile, content },
  })
}

// ── 重载配置 ─────────────────────────────────────────────────────────
function doReload() {
  if (!activeServerKey.value) return
  reloading.value = true
  window.__tshockSend?.({
    type: 'reload_tshock',
    msg_id: `cfg-reload-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

// ── 字段更新 ─────────────────────────────────────────────────────────
function setField(key, value) {
  configData.value = { ...configData.value, [key]: value }
  modified.value = true
}

// ── 消息处理 ─────────────────────────────────────────────────────────
function onWsMessage(e) {
  const pkt = e.detail
  const p   = pkt.payload || {}

  if (pkt.type === 'read_tshock_config_resp') {
    loading.value = false
    if (!p.success) {
      loadError.value = p.msg || '读取配置失败'
      return
    }
    try {
      const rawRoot = JSON.parse(p.content)
      // TShock 5.x 将所有设置包在 "Settings" 键下；兼容旧格式
      const hasWrapper = rawRoot.Settings && typeof rawRoot.Settings === 'object'
      const source     = hasWrapper ? rawRoot.Settings : rawRoot
      rawWrapper.value = hasWrapper ? rawRoot : null

      // ★ 严格以文件实际内容为准，不补充 schema 默认值
      //   · 保存时只会写回文件原有的字段，不会引入当前版本没有的键
      configData.value = { ...source }
      configLoaded.value = true
      modified.value     = false
      loadError.value    = ''
      if (!activeCat.value && categories.value.length > 0) {
        activeCat.value = categories.value[0]   // 默认"全部"
      }
    } catch (err) {
      loadError.value = `JSON 解析失败: ${err.message}`
    }
    return
  }

  if (pkt.type === 'write_tshock_config_resp') {
    saving.value = false
    if (p.success) {
      modified.value = false
      saveResult.value = { ok: true, msg: '配置已保存到服务器' }
    } else {
      saveResult.value = { ok: false, msg: p.msg || '保存失败' }
    }
    setTimeout(() => { saveResult.value = null }, 4000)
    return
  }

  if (pkt.type === 'reload_tshock_resp') {
    reloading.value = false
    saveResult.value = { ok: p.success ?? false, msg: p.msg || (p.success ? '重载成功' : '重载失败') }
    setTimeout(() => { saveResult.value = null }, 4000)
    return
  }
}

// ── 生命周期 ─────────────────────────────────────────────────────────
onMounted(() => {
  window.addEventListener('ws-message', onWsMessage)
  if (props.agentOnline && activeServerKey.value) loadConfig()
})
onUnmounted(() => {
  window.removeEventListener('ws-message', onWsMessage)
})

watch([activeServerKey, () => props.configFile], ([key]) => {
  if (!key) return
  configLoaded.value = false
  modified.value     = false
  configData.value   = {}
  rawWrapper.value   = null
  activeCat.value    = ''
  loadError.value    = ''
  if (props.agentOnline) loadConfig()
})

watch(() => props.agentOnline, (online) => {
  if (online && activeServerKey.value && !configLoaded.value && !loading.value) {
    loadConfig()
  }
})
</script>

<style scoped>
/* ── 页面容器 ── */
.cfg-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: #f8fafc;
}

/* ── 顶部标题栏 ── */
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
.cfg-header-left  { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.cfg-header-right { display: flex; align-items: center; gap: 8px; }
.cfg-title        { margin: 0; font-size: 18px; font-weight: 700; color: #0f172a; }
.cfg-subtitle {
  font-size: 12px; color: #64748b;
  background: #f1f5f9; border: 1px solid #e2e8f0;
  padding: 2px 8px; border-radius: 20px; font-family: monospace;
}
.cfg-modified-badge {
  font-size: 12px; color: #d97706;
  background: #fef3c7; border: 1px solid #fde68a;
  padding: 2px 8px; border-radius: 20px;
  animation: pulse-dot 1.5s ease-in-out infinite;
}
@keyframes pulse-dot { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

/* ── 按钮 ── */
.cfg-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 16px; border-radius: 8px; font-size: 13px;
  font-weight: 500; cursor: pointer; border: none;
  transition: all 0.15s;
}
.cfg-btn svg { width: 14px; height: 14px; flex-shrink: 0; }
.cfg-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.cfg-btn-outline {
  background: #fff; color: #374151;
  border: 1px solid #d1d5db;
}
.cfg-btn-outline:hover:not(:disabled) { background: #f9fafb; border-color: #9ca3af; }
.cfg-btn-primary {
  background: #3b82f6; color: #fff;
}
.cfg-btn-primary:hover:not(:disabled) { background: #2563eb; }

/* ── 状态区 ── */
.cfg-offline, .cfg-loading, .cfg-error, .cfg-empty {
  display: flex; align-items: center; justify-content: center;
  gap: 14px; padding: 60px 24px; color: #64748b;
  flex-direction: row; font-size: 14px;
}
.cfg-offline { flex-direction: row; }
.cfg-offline svg { width: 24px; height: 24px; color: #94a3b8; flex-shrink: 0; }
.cfg-error { flex-direction: row; align-items: flex-start; }
.cfg-error svg { width: 24px; height: 24px; color: #ef4444; flex-shrink: 0; margin-top: 2px; }
.cfg-error strong { color: #0f172a; font-size: 15px; }
.cfg-error p { margin: 4px 0 0; font-size: 13px; }
.cfg-loading { flex-direction: column; gap: 12px; }
.cfg-empty   { flex-direction: column; text-align: center; }
.cfg-empty-icon { font-size: 40px; }

.cfg-spinner {
  width: 28px; height: 28px;
  border: 3px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.spinning { animation: spin 0.7s linear infinite; }

/* ── 编辑器主体 ── */
.cfg-editor {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* ── 操作结果提示 ── */
.cfg-toast {
  display: flex; align-items: center; justify-content: space-between;
  margin: 12px 24px 0; padding: 10px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 500; flex-shrink: 0;
}
.cfg-toast-ok  { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.cfg-toast-err { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
.cfg-toast-close {
  background: none; border: none; cursor: pointer; font-size: 14px;
  color: inherit; opacity: 0.6; padding: 0 0 0 12px;
}
.cfg-toast-close:hover { opacity: 1; }

/* ── 搜索框 ── */
.cfg-search-bar {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 24px 8px;
  flex-shrink: 0;
}
.cfg-search-bar svg { width: 16px; height: 16px; color: #94a3b8; flex-shrink: 0; }
.cfg-search-input {
  flex: 1; border: 1px solid #e2e8f0; border-radius: 8px;
  padding: 8px 12px; font-size: 13px; outline: none;
  background: #fff; color: #1e293b;
  transition: border-color 0.15s;
}
.cfg-search-input:focus { border-color: #3b82f6; }
.cfg-search-clear {
  background: none; border: none; cursor: pointer;
  color: #94a3b8; font-size: 14px; padding: 4px;
}
.cfg-search-clear:hover { color: #64748b; }

/* ── 搜索结果区 ── */
.cfg-search-results {
  flex: 1; overflow-y: auto; padding: 8px 24px 20px;
}
.cfg-no-result {
  text-align: center; padding: 40px; color: #94a3b8; font-size: 14px;
}

/* ── 分类标签条 ── */
.cfg-cats {
  display: flex; flex-wrap: wrap; gap: 6px;
  padding: 12px 24px 8px;
  border-bottom: 1px solid #f1f5f9;
  flex-shrink: 0;
}
.cfg-cat-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 14px; border-radius: 20px; font-size: 12px;
  border: 1px solid #e2e8f0; background: #fff;
  color: #374151; cursor: pointer; transition: all 0.15s;
  font-weight: 500;
}
.cfg-cat-btn:hover       { background: #f8fafc; border-color: #94a3b8; }
.cfg-cat-btn.active      { background: #3b82f6; color: #fff; border-color: #3b82f6; }
.cfg-cat-count {
  background: rgba(0,0,0,0.1); border-radius: 10px;
  padding: 1px 6px; font-size: 10px;
}
.cfg-cat-btn.active .cfg-cat-count { background: rgba(255,255,255,0.25); }

/* ── 字段面板 ── */
.cfg-fields-panel {
  flex: 1; overflow-y: auto; padding: 16px 24px 24px;
}
.cfg-field-row {
  margin-bottom: 4px;
}
</style>
