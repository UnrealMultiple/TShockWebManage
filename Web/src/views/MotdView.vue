<template>
  <div class="cfg-page">
    <!-- ── 顶部标题栏 ── -->
    <div class="cfg-header">
      <div class="cfg-header-left">
        <h2 class="cfg-title">欢迎消息 (MOTD)</h2>
        <span class="cfg-subtitle">motd.txt</span>
        <span v-if="modified" class="cfg-modified-badge">● 未保存</span>
      </div>
      <div class="cfg-header-right">
        <button class="cfg-btn cfg-btn-outline" @click="loadMotd"
          :disabled="loading || !props.agentOnline || !activeServerKey">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
          </svg>
          刷新
        </button>
        <button class="cfg-btn cfg-btn-outline" @click="doReload"
          :disabled="!props.agentOnline || reloading || !motdLoaded">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 1 1-.49-3.18"/>
          </svg>
          {{ reloading ? '重载中…' : '立即重载' }}
        </button>
        <button class="cfg-btn cfg-btn-primary" @click="doSave"
          :disabled="!props.agentOnline || saving || !modified">
          <svg v-if="saving" viewBox="0 0 24 24" class="spinning" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </div>
    </div>

    <!-- Agent 离线 -->
    <div v-if="!props.agentOnline" class="cfg-offline">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <span>Agent 未连接，无法读取或保存 MOTD。请先启动服务器。</span>
    </div>

    <template v-else>
      <!-- 加载中 -->
      <div v-if="loading" class="cfg-loading">
        <div class="cfg-spinner"></div>
        <span>正在读取 MOTD…</span>
      </div>

      <!-- 读取失败 -->
      <div v-else-if="loadError" class="cfg-error">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <div>
          <strong>读取失败</strong>
          <p>{{ loadError }}</p>
          <button class="cfg-btn cfg-btn-outline" style="margin-top:8px" @click="loadMotd">重试</button>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="!motdLoaded" class="cfg-empty">
        <div class="cfg-empty-icon">📝</div>
        <p>点击刷新读取 MOTD 文件</p>
        <button class="cfg-btn cfg-btn-primary" @click="loadMotd">读取 MOTD</button>
      </div>

      <!-- 编辑器 -->
      <div v-else class="cfg-editor">
        <!-- Toast -->
        <div v-if="toast" :class="['cfg-toast', toast.ok ? 'cfg-toast-ok' : 'cfg-toast-err']">
          {{ toast.msg }}
          <button class="cfg-toast-close" @click="toast = null">✕</button>
        </div>

        <div class="motd-body">
          <!-- 左：编辑器 -->
          <div class="motd-editor-col">
            <div class="motd-col-label">编辑内容</div>
            <textarea
              class="motd-textarea"
              v-model="content"
              spellcheck="false"
              placeholder="在此输入欢迎消息内容…"
              @input="modified = true"
            />
          </div>

          <!-- 右：占位符 + 预览 -->
          <div class="motd-ref-col">
            <div class="motd-col-label">可用占位符 <span class="motd-hint">（点击插入）</span></div>
            <div class="motd-ref-list">
              <div class="motd-ref-item" v-for="p in PLACEHOLDERS" :key="p.tag" @click="insertTag(p.tag)">
                <code class="motd-ref-tag">{{ p.tag }}</code>
                <span class="motd-ref-desc">{{ p.desc }}</span>
              </div>
            </div>
            <div class="motd-col-label" style="margin-top:14px">颜色代码</div>
            <div class="motd-ref-note">
              格式：<code>[c/RRGGBB:文字]</code><br>
              例：<code>[c/FF0000:红色]</code>&nbsp;<code>[c/55d284:绿色]</code>
            </div>
            <div class="motd-col-label" style="margin-top:14px">预览</div>
            <div class="motd-preview" v-html="previewHtml" />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, inject } from 'vue'

const props = defineProps({
  agentOnline: { type: Boolean, default: false },
  wsState:     { type: String,  default: '' },
})

const activeServerKey = inject('activeServerKey', ref(''))

// ── 状态 ─────────────────────────────────────────────────────────
const content    = ref('')
const motdPath   = ref('')
const loading    = ref(false)
const loadError  = ref('')
const motdLoaded = ref(false)
const saving     = ref(false)
const reloading  = ref(false)
const modified   = ref(false)
const toast      = ref(null)

const PLACEHOLDERS = [
  { tag: '%map%',           desc: '当前地图名称' },
  { tag: '%onlineplayers%', desc: '当前在线玩家数' },
  { tag: '%players%',       desc: '在线玩家名单（逗号分隔）' },
  { tag: '%serverslots%',   desc: '服务器最大槽位数' },
  { tag: '%specifier%',     desc: '命令前缀（如 /）' },
]

// ── WebSocket 消息监听（不过滤 agent_key，与 TShockConfigView 一致）──
function onWsMessage(e) {
  const pkt = e.detail
  const p   = pkt?.payload || {}

  if (pkt.type === 'read_motd_resp') {
    loading.value = false
    if (!p.success) { loadError.value = p.msg || '读取失败'; return }
    content.value    = p.content ?? ''
    motdPath.value   = p.path   ?? ''
    motdLoaded.value = true
    modified.value   = false
    loadError.value  = ''
    return
  }
  if (pkt.type === 'write_motd_resp') {
    saving.value = false
    if (p.success) {
      modified.value = false
      if (p.path) motdPath.value = p.path
      showToast(true, '保存成功')
    } else {
      showToast(false, p.msg || '保存失败')
    }
    return
  }
  if (pkt.type === 'reload_tshock_resp') {
    reloading.value = false
    showToast(p.success ?? false, p.msg || (p.success ? '重载成功' : '重载失败'))
    return
  }
}

onMounted(() => {
  window.addEventListener('ws-message', onWsMessage)
  if (props.agentOnline && activeServerKey.value) loadMotd()
})
onUnmounted(() => window.removeEventListener('ws-message', onWsMessage))

watch([activeServerKey, () => props.agentOnline], ([key]) => {
  if (key && props.agentOnline && !motdLoaded.value && !loading.value) loadMotd()
})

// ── 读取 ─────────────────────────────────────────────────────────
function loadMotd() {
  if (!activeServerKey.value) return
  loading.value    = true
  loadError.value  = ''
  motdLoaded.value = false
  window.__tshockSend?.({
    type: 'read_motd', msg_id: Date.now().toString(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value }
  })
}

// ── 保存 ─────────────────────────────────────────────────────────
function doSave() {
  if (!activeServerKey.value) return
  saving.value = true
  window.__tshockSend?.({
    type: 'write_motd', msg_id: Date.now().toString(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, content: content.value }
  })
}

// ── 热重载 ───────────────────────────────────────────────────────
function doReload() {
  if (!activeServerKey.value) return
  reloading.value = true
  window.__tshockSend?.({
    type: 'reload_tshock', msg_id: Date.now().toString(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value }
  })
}

// ── 占位符插入 ───────────────────────────────────────────────────
function insertTag(tag) {
  content.value += tag
  modified.value = true
}

// ── 预览 ─────────────────────────────────────────────────────────
const previewHtml = computed(() => {
  if (!content.value) return '<span style="color:#64748b">（空）</span>'
  return content.value
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\[c\/([0-9a-fA-F]{6}):([^\]]*)\]/g,
      (_, hex, text) => `<span style="color:#${hex}">${text}</span>`)
    .replace(/\n/g, '<br>')
})

function showToast(ok, msg) {
  toast.value = { ok, msg }
  setTimeout(() => { toast.value = null }, 4000)
}
</script>

<style scoped>
/* ── 页面根容器（与 TShockConfigView 完全一致） ── */
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
  max-width: 380px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  display: inline-block; vertical-align: middle;
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

/* ── 状态区（与 TShockConfigView 完全一致） ── */
.cfg-offline, .cfg-loading, .cfg-error, .cfg-empty {
  display: flex; align-items: center; justify-content: center;
  gap: 14px; padding: 60px 24px; color: #64748b;
  font-size: 14px;
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
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

/* ── Toast ── */
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

/* ── 编辑器 + 参考面板 布局 ── */
.motd-body {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 20px;
  padding: 20px 24px;
  align-items: start;
  flex: 1;
}
@media (max-width: 860px) { .motd-body { grid-template-columns: 1fr; } }

.motd-col-label {
  font-size: 11px; font-weight: 700; color: #64748b;
  text-transform: uppercase; letter-spacing: .06em;
  margin-bottom: 8px;
}
.motd-hint { font-weight: 400; text-transform: none; letter-spacing: 0; color: #94a3b8; }

/* ── textarea ── */
.motd-textarea {
  width: 100%; min-height: 360px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px; line-height: 1.7;
  padding: 14px 16px;
  border: 1.5px solid #e2e8f0; border-radius: 10px;
  background: #f8fafc; color: #1e293b;
  resize: vertical; outline: none; box-sizing: border-box;
  transition: border-color 0.15s;
}
.motd-textarea:focus { border-color: #3b82f6; background: #fff; }

/* ── 参考面板 ── */
.motd-ref-list { display: flex; flex-direction: column; gap: 5px; }
.motd-ref-item {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 10px;
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 7px;
  cursor: pointer; transition: background 0.12s;
}
.motd-ref-item:hover { background: #eff6ff; border-color: #bfdbfe; }
.motd-ref-tag  { font-size: 11px; background: #e0e7ff; color: #3730a3; padding: 2px 6px; border-radius: 4px; white-space: nowrap; }
.motd-ref-desc { font-size: 12px; color: #64748b; }

.motd-ref-note {
  font-size: 12px; color: #64748b;
  background: #f8fafc; border: 1px solid #e2e8f0;
  border-radius: 7px; padding: 10px 12px; line-height: 2;
}
.motd-ref-note code { background: #e0e7ff; color: #3730a3; padding: 1px 5px; border-radius: 4px; }

/* ── 游戏内预览 ── */
.motd-preview {
  background: #1e2d3d; color: #e2e8f0; border-radius: 8px;
  padding: 12px 14px; font-size: 13px; line-height: 1.9;
  min-height: 56px; word-break: break-word;
}
</style>
