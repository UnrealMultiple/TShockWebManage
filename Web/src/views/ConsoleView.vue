<template>
  <div class="console-layout">
    <!-- 主体 -->
    <main class="console-main">
      <!-- 日志区 -->
      <div class="log-panel">
        <div class="panel-header">
          <span>控制台输出</span>
          <div class="panel-header-right">
            <span class="active-server-name" v-if="activeKey">{{ activeServerName }}</span>
            <span class="active-server-name muted" v-else>未选择服务器</span>
            <button class="clear-btn" @click="logs = []">清空</button>
          </div>
        </div>
        <div class="log-box" ref="logBox">
          <div v-for="(l, i) in logs" :key="i" class="log-row">
            <span class="log-time">{{ l.time }}</span>
            <span :class="['log-tag', l.tagClass]">{{ logTypeLabel(l.type) }}</span>
            <span class="log-content">{{ l.content }}</span>
          </div>
          <div v-if="!logs.length" class="log-empty">等待日志输出…</div>
        </div>
      </div>

      <!-- 指令输入区 -->
      <div class="input-panel">
        <div class="input-row">
          <div class="input-group flex-1">
            <label>指令</label>
            <input
              v-model="cmd"
              placeholder="如 /kick PlayerA 或 /tp Player1 Player2"
              @keydown="onCommandKeydown"
              ref="cmdInput"
              :disabled="sendDisabled"
            />
          </div>
          <button
            class="send-btn"
            @click="doSend"
            :disabled="sendDisabled || !cmd.trim()"
          >
            发送
          </button>
        </div>
        <div class="input-hint">
          <span>Agent 在线:
            <span :class="agentOnline ? 'status-online' : 'status-offline'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <template v-if="agentOnline">
                  <circle cx="12" cy="12" r="10"/><polyline points="9 12 11 14 15 10"/>
                </template>
                <template v-else>
                  <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
                </template>
              </svg>
              {{ agentOnline ? '已连接' : '未连接' }}
            </span>
          </span>
          <span v-if="!canUseConsole" class="hint-server">缺少控制台权限</span>
          <span v-if="activeKey" class="hint-server">目标：{{ activeServerName }}</span>
          <span v-else class="hint-server">请选择服务器</span>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, inject, watch } from 'vue'

const props = defineProps({
  wsState:     { type: String, default: 'disconnected' },
  agentOnline: { type: Boolean, default: false },
})

const logs     = ref([])
const cmd      = ref('')
const logBox   = ref(null)
const cmdInput = ref(null)
const commandHistory = ref([])
const historyIndex = ref(-1)
const MAX_LOGS = 500

// 从 MainLayout 注入全局服务器状态
const myServers = inject('myServers', ref([]))
const activeKey = inject('activeServerKey', ref(''))
const activeServer = inject('activeServer', ref(null))
const hasPerm = inject('hasPerm', () => false)

const canUseConsole = computed(() => {
  const role = activeServer.value?.server_role
  return role === 'owner' || role === 'web_staff' || hasPerm('panel.console')
})

const sendDisabled = computed(() => {
  return props.wsState !== 'connected' || !props.agentOnline || !canUseConsole.value || !activeKey.value
})

const activeServerName = computed(() => {
  if (activeServer.value?.name) return activeServer.value.name
  const s = myServers.value?.find(s => s.agent_key === activeKey.value)
  return s ? s.name : (activeKey.value || '')
})

function addLog(type, content, tagClass = 'tag-sys') {
  logs.value.push({
    time: new Date().toLocaleTimeString(),
    type,
    content: String(content ?? ''),
    tagClass
  })
  if (logs.value.length > MAX_LOGS) {
    logs.value.splice(0, logs.value.length - MAX_LOGS)
  }
  nextTick(() => {
    if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight
  })
}

function logTypeLabel(type) {
  return ({
    sys: '系统',
    error: '错误',
    log: '日志',
    response: '返回',
    send: '发送',
  })[type] || type
}

function normalizeAgentKey(v) {
  return String(v ?? '').trim()
}

function isForActiveServer(pkt) {
  const metaKey = normalizeAgentKey(pkt.metadata?.agent_key)
  if (!metaKey) return true
  return metaKey === normalizeAgentKey(activeKey.value)
}

// 接收来自 MainLayout 广播的 WebSocket 消息
function onWsMessage(e) {
  const pkt = e.detail
  if (!isForActiveServer(pkt)) return
  const p   = pkt.payload || {}
  switch (pkt.type) {
    case 'auth':
      addLog('sys', `身份验证成功`, 'tag-sys')
      break
    case 'error':
      addLog('error', pkt.msg || '未知错误', 'tag-error')
      break
    case 'log':
      addLog('log', p.content || '', 'tag-log')
      break
    case 'cmd_resp':
      addLog(
        'response',
        p.output || '(无输出)',
        p.success ? 'tag-ok' : 'tag-error'
      )
      break
  }
}

function onCommandKeydown(e) {
  if (e.isComposing) return
  if (e.key === 'Enter') {
    e.preventDefault()
    doSend()
    return
  }
  if (e.key === 'ArrowUp') {
    if (!commandHistory.value.length) return
    e.preventDefault()
    if (historyIndex.value < 0) historyIndex.value = commandHistory.value.length - 1
    else historyIndex.value = Math.max(0, historyIndex.value - 1)
    cmd.value = commandHistory.value[historyIndex.value] || ''
    return
  }
  if (e.key === 'ArrowDown') {
    if (historyIndex.value < 0) return
    e.preventDefault()
    historyIndex.value += 1
    if (historyIndex.value >= commandHistory.value.length) {
      historyIndex.value = -1
      cmd.value = ''
    } else {
      cmd.value = commandHistory.value[historyIndex.value] || ''
    }
  }
}

function doSend() {
  if (!canUseConsole.value) return
  if (!activeKey.value) return
  if (!cmd.value.trim()) return
  if (!props.agentOnline) return
  if (props.wsState !== 'connected') return

  const rawCmd = cmd.value.trim()
  const packet = {
    type:      'cmd',
    msg_id:    Math.random().toString(36).substring(2),
    timestamp: Date.now(),
    payload:   {
      raw_cmd:   rawCmd,
      agent_key: activeKey.value || undefined,
    }
  }
  const sent = window.__tshockSend?.(packet)
  if (sent === false) {
    addLog('error', 'WebSocket 未连接，发送失败', 'tag-error')
    return
  }
  if (commandHistory.value[commandHistory.value.length - 1] !== rawCmd) {
    commandHistory.value.push(rawCmd)
    if (commandHistory.value.length > 50) commandHistory.value.shift()
  }
  historyIndex.value = -1
  addLog('send', `[${activeServerName.value}] ${rawCmd}`, 'tag-send')
  cmd.value = ''
}

onMounted(() => {
  window.addEventListener('ws-message', onWsMessage)
})
onUnmounted(() => {
  window.removeEventListener('ws-message', onWsMessage)
})

watch(activeKey, () => {
  logs.value = []
  historyIndex.value = -1
})
</script>

<style scoped>
.console-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* ── 主体 ── */
.console-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px;
  gap: 12px;
}

/* ── 日志面板 ── */
.log-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
  min-height: 0;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
}
.panel-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.active-server-name {
  font-size: 12px;
  font-weight: 600;
  color: #3b82f6;
  background: #eff6ff;
  padding: 2px 9px;
  border-radius: 5px;
}
.active-server-name.muted { color: #94a3b8; background: #f1f5f9; }
.hint-server {
  font-size: 0.78rem;
  color: #3b82f6;
  margin-left: 8px;
}
.clear-btn {
  background: transparent;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  color: #94a3b8;
  font-size: 12px;
  padding: 2px 10px;
  cursor: pointer;
  transition: all .15s;
}
.clear-btn:hover { background: #f1f5f9; color: #475569; }

.log-box {
  flex: 1;
  overflow-y: auto;
  padding: 10px 14px;
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  background: #f8fafc;
}
.log-empty { color: #cbd5e1; text-align: center; padding: 40px 0; font-size: 14px; }

.log-row   { display: flex; align-items: baseline; gap: 8px; padding: 2px 0; }
.log-time  { color: #cbd5e1; font-size: 11px; flex-shrink: 0; }
.log-tag   {
  font-size: 11px; font-weight: 700; padding: 1px 6px;
  border-radius: 4px; flex-shrink: 0; min-width: 42px; text-align: center;
}
.log-content { color: #334155; word-break: break-word; white-space: pre-wrap; }

.tag-sys   { background: #dbeafe; color: #1d4ed8; }
.tag-log   { background: #f1f5f9; color: #64748b; }
.tag-ok    { background: #dcfce7; color: #15803d; }
.tag-error { background: #fee2e2; color: #dc2626; }
.tag-warn  { background: #fef3c7; color: #b45309; }
.tag-send  { background: #ede9fe; color: #7c3aed; }

/* ── 指令输入 ── */
.input-panel {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 14px;
  flex-shrink: 0;
}
.input-row {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}
.input-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.input-group label {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
}
.input-group input {
  padding: 9px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 7px;
  color: #0f172a;
  font-size: 14px;
  outline: none;
  transition: border-color .15s, box-shadow .15s;
}
.input-group input:focus   { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.1); }
.input-group input:disabled { opacity: .4; cursor: not-allowed; }
.flex-1 { flex: 1; }

.send-btn {
  padding: 9px 24px;
  background: #2563eb;
  border: none;
  border-radius: 7px;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background .15s;
  flex-shrink: 0;
  align-self: flex-end;
}
.send-btn:hover:not(:disabled) { background: #1d4ed8; }
.send-btn:disabled { opacity: .4; cursor: not-allowed; }

.input-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #94a3b8;
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}
.status-online {
  display: inline-flex; align-items: center; gap: 3px;
  color: #16a34a; font-weight: 500;
}
.status-offline {
  display: inline-flex; align-items: center; gap: 3px;
  color: #dc2626; font-weight: 500;
}
.status-online svg, .status-offline svg { width: 13px; height: 13px; }
</style>
