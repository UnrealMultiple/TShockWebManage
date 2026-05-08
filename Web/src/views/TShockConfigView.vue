<template>
  <div class="cfg-page">
    <!-- ── 顶部标题栏 ── -->
    <PageHeader :title="fileConf.title" :subtitle="fileConf.subtitle">
      <template #meta>
        <span v-if="modified" class="cfg-modified-badge">● 未保存</span>
      </template>
      <template #actions>
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
          :disabled="!modified || saving || !agentOnline || !activeServerKey || (editorMode === 'json' && !!jsonError)">
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
      </template>
    </PageHeader>

    <!-- Agent 离线提示 -->
    <AgentOfflineNotice v-if="!agentOnline" message="Agent 未连接，无法读取或保存配置。请先启动服务器。" />

    <template v-else>
      <!-- 加载中 -->
      <div v-if="loading" class="cfg-loading">
        <div class="cfg-spinner"></div>
        <span>正在从服务器读取配置…</span>
      </div>

      <!-- 读取失败 -->
      <AgentOfflineNotice v-else-if="loadError" type="error" :message="loadError" show-retry :retry-label="'重试'" @retry="loadConfig" />

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

        <div class="cfg-mode-bar">
          <div class="cfg-mode-tabs">
            <button :class="['cfg-mode-btn', { active: editorMode === 'visual' }]" @click="switchEditorMode('visual')">
              可视化
            </button>
            <button :class="['cfg-mode-btn', { active: editorMode === 'json' }]" @click="switchEditorMode('json')">
              JSON
            </button>
          </div>
          <button v-if="editorMode === 'json'" class="cfg-btn cfg-btn-outline cfg-format-btn" @click="formatJsonText">
            格式化
          </button>
          <span v-if="editorMode === 'json' && jsonError" class="cfg-json-error">{{ jsonErrorSummary }}</span>
        </div>

        <template v-if="editorMode === 'visual'">
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
        </template>

        <div v-else class="cfg-json-panel">
          <div class="cfg-json-editor" :class="{ invalid: !!jsonError }">
            <div ref="jsonLineGutterEl" class="cfg-json-gutter" aria-hidden="true">
              <span v-for="line in jsonLineNumbers" :key="line" :class="{ error: line === jsonErrorLine }">{{ line }}</span>
            </div>
            <pre ref="jsonHighlightEl" class="cfg-json-highlight" aria-hidden="true"><code v-html="highlightedJson"></code></pre>
            <textarea
              ref="jsonTextareaEl"
              class="cfg-json-input"
              v-model="rawJsonText"
              spellcheck="false"
              @input="onRawJsonInput"
              @scroll="syncJsonScroll"
              @keydown.tab.prevent="insertJsonIndent"
            ></textarea>
          </div>
          <div v-if="jsonError" class="cfg-json-err">
            <div class="cfg-json-err-head">
              <strong>JSON 格式不正确</strong>
              <button v-if="jsonErrorPos" class="cfg-json-err-jump" @click="jumpToJsonError">定位到错误</button>
            </div>
            <div class="cfg-json-err-msg">{{ jsonError }}</div>
            <div v-if="jsonErrorPos" class="cfg-json-err-meta">
              第 {{ jsonErrorPos.line }} 行，第 {{ jsonErrorPos.col }} 列附近
            </div>
            <div v-if="jsonErrorContext.length" class="cfg-json-err-context">
              <template v-for="row in jsonErrorContext" :key="`${row.line}-${row.isCaret ? 'caret' : 'code'}`">
                <div v-if="!row.isCaret" :class="['cfg-json-err-row', { error: row.isError }]">
                  <span class="cfg-json-err-no">{{ row.line }}</span>
                  <code>{{ row.text || ' ' }}</code>
                </div>
                <div v-else class="cfg-json-err-row cfg-json-err-caret">
                  <span class="cfg-json-err-no"></span>
                  <code :style="{ paddingLeft: `${Math.max(0, row.col - 1)}ch` }">^</code>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, inject, nextTick } from 'vue'
import { CONFIG_FILE_MAP } from '@/config/tshock_schema.js'
import FieldControl from '@/components/config/FieldControl.vue'
import AgentOfflineNotice from '@/components/AgentOfflineNotice.vue'
import PageHeader from '@/components/PageHeader.vue'

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
const editorMode   = ref('visual')
const rawJsonText  = ref('')
const jsonError    = ref('')
const jsonErrorPos = ref(null)
const jsonTextareaEl = ref(null)
const jsonHighlightEl = ref(null)
const jsonLineGutterEl = ref(null)

const fileConf = computed(() => CONFIG_FILE_MAP[props.configFile] || CONFIG_FILE_MAP.config)
const schema   = computed(() => fileConf.value.schema)
const jsonLineNumbers = computed(() => {
  const count = Math.max(1, String(rawJsonText.value || '').split('\n').length)
  return Array.from({ length: count }, (_, index) => index + 1)
})
const jsonErrorLine = computed(() => jsonErrorPos.value?.line || 0)
const jsonErrorSummary = computed(() => {
  if (!jsonError.value) return ''
  return jsonErrorPos.value
    ? `第 ${jsonErrorPos.value.line} 行附近有格式问题`
    : 'JSON 格式不正确'
})
const jsonErrorContext = computed(() => getJsonErrorContext(rawJsonText.value, jsonErrorPos.value))
const highlightedJson = computed(() => highlightJson(rawJsonText.value, jsonErrorLine.value))

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

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function highlightJsonLine(value) {
  const text = String(value || '')
  const tokenPattern = /("(?:\\u[\da-fA-F]{4}|\\[^u]|[^\\"])*"(\s*:)?|\btrue\b|\bfalse\b|\bnull\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g
  let html = ''
  let cursor = 0
  for (const match of text.matchAll(tokenPattern)) {
    const token = match[0]
    const index = match.index ?? 0
    html += escapeHtml(text.slice(cursor, index))
    let cls = 'json-number'
    if (token.startsWith('"')) cls = /:\s*$/.test(token) ? 'json-key' : 'json-string'
    else if (token === 'true' || token === 'false') cls = 'json-bool'
    else if (token === 'null') cls = 'json-null'
    html += `<span class="${cls}">${escapeHtml(token)}</span>`
    cursor = index + token.length
  }
  html += escapeHtml(text.slice(cursor))
  return html
}

function highlightJson(value, errorLine = 0) {
  const text = String(value || '')
  if (!text) return '<span class="json-line"><span class="json-muted">{}</span></span>'
  return text.split('\n').map((line, index) => {
    const lineNo = index + 1
    const cls = lineNo === errorLine ? 'json-line is-error' : 'json-line'
    return `<span class="${cls}">${highlightJsonLine(line) || '&nbsp;'}</span>`
  }).join('')
}

function extractConfigSource(rawRoot) {
  if (!rawRoot || typeof rawRoot !== 'object' || Array.isArray(rawRoot)) {
    throw new Error('JSON 根节点必须是对象')
  }
  const hasWrapper = rawRoot.Settings && typeof rawRoot.Settings === 'object' && !Array.isArray(rawRoot.Settings)
  if (rawRoot.Settings && !hasWrapper) {
    throw new Error('Settings 必须是对象')
  }
  return {
    source: hasWrapper ? rawRoot.Settings : rawRoot,
    wrapper: hasWrapper ? rawRoot : null,
  }
}

function applyConfigRoot(rawRoot, { markModified = false, updateRaw = true } = {}) {
  const { source, wrapper } = extractConfigSource(rawRoot)
  rawWrapper.value = wrapper
  configData.value = { ...source }
  configLoaded.value = true
  modified.value = markModified
  loadError.value = ''
  jsonError.value = ''
  jsonErrorPos.value = null
  if (updateRaw) rawJsonText.value = JSON.stringify(rawRoot, null, 2)
  if (!activeCat.value && categories.value.length > 0) {
    activeCat.value = categories.value[0]
  }
}

function cleanVisualConfigData() {
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
  return cleaned
}

function buildVisualConfigRoot() {
  const cleaned = cleanVisualConfigData()
  return rawWrapper.value
    ? { ...rawWrapper.value, Settings: cleaned }
    : cleaned
}

function syncRawFromVisual() {
  rawJsonText.value = JSON.stringify(buildVisualConfigRoot(), null, 2)
  jsonError.value = ''
  jsonErrorPos.value = null
  nextTick(syncJsonScroll)
}

function parseRawJsonText() {
  try {
    const rawRoot = JSON.parse(rawJsonText.value)
    extractConfigSource(rawRoot)
    jsonError.value = ''
    jsonErrorPos.value = null
    return rawRoot
  } catch (err) {
    jsonErrorPos.value = parseJsonErrorPosition(rawJsonText.value, err)
    jsonError.value = formatFriendlyJsonError(rawJsonText.value, err)
    return null
  }
}

function parseJsonErrorPosition(text, err) {
  const msg = String(err?.message || '')
  const lineCol = msg.match(/line\s+(\d+)\s+column\s+(\d+)/i)
  if (lineCol) {
    const line = Number(lineCol[1])
    const col = Number(lineCol[2])
    const lines = String(text || '').split('\n')
    const idx = lines.slice(0, Math.max(0, line - 1)).reduce((sum, lineText) => sum + lineText.length + 1, 0) + Math.max(0, col - 1)
    return { idx: Math.min(idx, text.length), line, col }
  }

  const posMatch = msg.match(/position\s+(\d+)/i)
  if (!posMatch) return null
  const idx = Math.min(Number(posMatch[1]), text.length)
  if (!Number.isFinite(idx) || idx < 0) return null
  const head = text.slice(0, idx)
  const lines = head.split('\n')
  return {
    idx,
    line: lines.length,
    col: lines[lines.length - 1].length + 1,
  }
}

function clampJsonContextLine(lineText, col = 1, isError = false) {
  const text = String(lineText ?? '')
  if (text.length <= 160) return { text, col }
  if (!isError) return { text: `${text.slice(0, 157)}...`, col: 1 }
  const safeCol = Math.max(1, col || 1)
  const start = Math.max(0, safeCol - 81)
  const end = Math.min(text.length, start + 160)
  const prefix = start > 0 ? '...' : ''
  const suffix = end < text.length ? '...' : ''
  return {
    text: `${prefix}${text.slice(start, end)}${suffix}`,
    col: safeCol - start + prefix.length,
  }
}

function getJsonErrorContext(text, pos, radius = 2) {
  if (!pos) return []
  const lines = String(text || '').split('\n')
  const errorLine = Math.max(1, pos.line || 1)
  const start = Math.max(1, errorLine - radius)
  const end = Math.min(lines.length, errorLine + radius)
  const rows = []
  for (let lineNo = start; lineNo <= end; lineNo += 1) {
    const isError = lineNo === errorLine
    const lineInfo = clampJsonContextLine(lines[lineNo - 1] ?? '', pos.col || 1, isError)
    rows.push({ line: lineNo, text: lineInfo.text, isError })
    if (isError) rows.push({ line: lineNo, isCaret: true, col: lineInfo.col })
  }
  return rows
}

function jumpToJsonError() {
  const pos = jsonErrorPos.value
  const el = jsonTextareaEl.value
  if (!pos || !el) return
  const lineHeight = parseFloat(getComputedStyle(el).lineHeight) || 21
  const colWidth = Math.max(7, (parseFloat(getComputedStyle(el).fontSize) || 13) * 0.62)
  el.focus()
  el.scrollTop = Math.max(0, (pos.line - 3) * lineHeight)
  el.scrollLeft = Math.max(0, (pos.col - 36) * colWidth)
  el.setSelectionRange(pos.idx ?? 0, pos.idx ?? 0)
  syncJsonScroll({ target: el })
}

function friendlyJsonHint(err) {
  const msg = String(err?.message || '')
  if (/Expected double-quoted property name/i.test(msg)) {
    return '对象属性名必须使用英文双引号，也可能是上一项末尾多了逗号。'
  }
  if (/Unexpected end of JSON input/i.test(msg)) {
    return '内容还没有写完整，请检查结尾处是否缺少括号、方括号或引号。'
  }
  if (/Unterminated string/i.test(msg)) {
    return '字符串没有正确结束，请检查是否缺少英文双引号。'
  }
  if (/Bad control character/i.test(msg)) {
    return '字符串中包含未转义的换行或控制字符。'
  }
  if (/Unexpected token/i.test(msg) && /}/.test(msg)) {
    return '可能存在多余逗号，或对象里缺少有效的键值对。'
  }
  if (/Unexpected string/i.test(msg)) {
    return '可能缺少逗号，或键和值之间缺少冒号。'
  }
  if (/Unexpected non-whitespace character/i.test(msg)) {
    return 'JSON 根节点后面还有多余内容。'
  }
  return '请检查逗号、冒号、英文双引号和括号是否成对。'
}

function formatFriendlyJsonError(text, err) {
  const pos = parseJsonErrorPosition(text, err)
  const hint = friendlyJsonHint(err)
  return pos
    ? `JSON 格式不正确：第 ${pos.line} 行，第 ${pos.col} 列附近。${hint}`
    : `JSON 格式不正确：${hint}`
}

function switchEditorMode(mode) {
  if (mode === editorMode.value) return
  if (mode === 'json') {
    syncRawFromVisual()
  } else {
    const rawRoot = parseRawJsonText()
    if (!rawRoot) return
    applyConfigRoot(rawRoot, { markModified: modified.value, updateRaw: false })
  }
  editorMode.value = mode
}

function onRawJsonInput() {
  modified.value = true
  const rawRoot = parseRawJsonText()
  if (!rawRoot) return
  applyConfigRoot(rawRoot, { markModified: true, updateRaw: false })
}

function formatJsonText() {
  const rawRoot = parseRawJsonText()
  if (!rawRoot) return
  rawJsonText.value = JSON.stringify(rawRoot, null, 2)
  applyConfigRoot(rawRoot, { markModified: true, updateRaw: false })
  modified.value = true
  nextTick(syncJsonScroll)
}

function syncJsonScroll(event) {
  const source = event?.target
  const target = jsonHighlightEl.value
  if (!source || !target) return
  target.scrollTop = source.scrollTop
  target.scrollLeft = source.scrollLeft
  if (jsonLineGutterEl.value) jsonLineGutterEl.value.scrollTop = source.scrollTop
}

function insertJsonIndent(event) {
  const el = event.target
  const start = el.selectionStart
  const end = el.selectionEnd
  rawJsonText.value = rawJsonText.value.slice(0, start) + '  ' + rawJsonText.value.slice(end)
  onRawJsonInput()
  nextTick(() => {
    el.selectionStart = start + 2
    el.selectionEnd = start + 2
    syncJsonScroll({ target: el })
  })
}

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
  let content = ''
  if (editorMode.value === 'json') {
    const rawRoot = parseRawJsonText()
    if (!rawRoot) return
    applyConfigRoot(rawRoot, { markModified: true, updateRaw: false })
    content = rawJsonText.value
  } else {
    content = JSON.stringify(buildVisualConfigRoot(), null, 2)
  }

  saving.value = true
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
      applyConfigRoot(rawRoot, { markModified: false, updateRaw: true })
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
  rawJsonText.value  = ''
  jsonError.value    = ''
  jsonErrorPos.value = null
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
.cfg-loading, .cfg-error, .cfg-empty {
  display: flex; align-items: center; justify-content: center;
  gap: 14px; padding: 60px 24px; color: #64748b;
  flex-direction: row; font-size: 14px;
}
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

/* ── 编辑模式 ── */
.cfg-mode-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 24px 0;
  flex-shrink: 0;
}
.cfg-mode-tabs {
  display: inline-flex;
  align-items: center;
  padding: 3px;
  background: #e2e8f0;
  border-radius: 8px;
}
.cfg-mode-btn {
  border: none;
  background: transparent;
  color: #475569;
  border-radius: 5px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.cfg-mode-btn.active {
  background: #fff;
  color: #1d4ed8;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}
.cfg-format-btn {
  padding: 6px 12px;
}
.cfg-json-error {
  min-width: 0;
  color: #dc2626;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

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

/* ── JSON 高亮编辑器 ── */
.cfg-json-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 12px 24px 24px;
  overflow: hidden;
}
.cfg-json-editor {
  position: relative;
  flex: 1;
  min-height: 0;
  min-height: 320px;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #0f172a;
  overflow: hidden;
}
.cfg-json-editor.invalid {
  border-color: #fca5a5;
  box-shadow: 0 0 0 3px rgba(248, 113, 113, 0.16);
}
.cfg-json-gutter {
  position: absolute;
  inset: 0 auto 0 0;
  z-index: 2;
  width: 48px;
  padding: 16px 0;
  box-sizing: border-box;
  overflow: hidden;
  border-right: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.96);
  color: #64748b;
  font-family: 'Cascadia Code', 'SFMono-Regular', Consolas, monospace;
  font-size: 12px;
  line-height: 1.7875;
  text-align: right;
}
.cfg-json-gutter span {
  display: block;
  height: 21.45px;
  padding: 0 10px 0 4px;
  box-sizing: border-box;
}
.cfg-json-gutter span.error {
  color: #fecaca;
  background: rgba(248, 113, 113, 0.18);
  font-weight: 700;
}
.cfg-json-highlight,
.cfg-json-input {
  position: absolute;
  inset: 0;
  margin: 0;
  padding: 16px 18px 16px 64px;
  border: none;
  box-sizing: border-box;
  font-family: 'Cascadia Code', 'SFMono-Regular', Consolas, monospace;
  font-size: 13px;
  line-height: 1.65;
  tab-size: 2;
  white-space: pre;
  overflow: auto;
}
.cfg-json-highlight {
  color: #cbd5e1;
  pointer-events: none;
}
.cfg-json-highlight code {
  font: inherit;
}
.cfg-json-highlight :deep(.json-line) {
  display: block;
  width: max-content;
  min-width: 100%;
  min-height: 1.65em;
}
.cfg-json-highlight :deep(.json-line.is-error) {
  background: rgba(248, 113, 113, 0.16);
  box-shadow: inset 3px 0 0 #f87171;
}
.cfg-json-input {
  resize: none;
  outline: none;
  background: transparent;
  color: transparent;
  caret-color: #f8fafc;
  -webkit-text-fill-color: transparent;
}
.cfg-json-input::selection {
  background: rgba(59, 130, 246, 0.35);
}
.cfg-json-input::-webkit-scrollbar,
.cfg-json-highlight::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}
.cfg-json-input::-webkit-scrollbar-thumb,
.cfg-json-highlight::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.35);
  border-radius: 999px;
}
.cfg-json-highlight :deep(.json-key) { color: #93c5fd; }
.cfg-json-highlight :deep(.json-string) { color: #86efac; }
.cfg-json-highlight :deep(.json-number) { color: #fbbf24; }
.cfg-json-highlight :deep(.json-bool) { color: #f0abfc; }
.cfg-json-highlight :deep(.json-null) { color: #94a3b8; }
.cfg-json-highlight :deep(.json-muted) { color: #64748b; }
.cfg-json-err {
  flex-shrink: 0;
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #fef2f2;
  color: #7f1d1d;
  font-size: 12.5px;
  line-height: 1.5;
}
.cfg-json-err-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 4px;
}
.cfg-json-err-msg {
  color: #991b1b;
}
.cfg-json-err-meta {
  margin-top: 2px;
  color: #b91c1c;
}
.cfg-json-err-jump {
  flex-shrink: 0;
  border: 1px solid #f87171;
  background: #fff;
  color: #b91c1c;
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 12px;
  cursor: pointer;
}
.cfg-json-err-jump:hover {
  background: #fee2e2;
}
.cfg-json-err-context {
  margin-top: 8px;
  padding: 6px 0;
  border: 1px solid #fecaca;
  border-radius: 6px;
  background: #fff;
  overflow-x: auto;
  font-family: ui-monospace, 'SFMono-Regular', Consolas, monospace;
  font-size: 12px;
}
.cfg-json-err-row {
  display: flex;
  min-width: max-content;
  white-space: pre;
  color: #111827;
}
.cfg-json-err-row.error {
  background: #fee2e2;
}
.cfg-json-err-row code {
  font: inherit;
}
.cfg-json-err-no {
  width: 42px;
  padding: 0 8px;
  box-sizing: border-box;
  text-align: right;
  color: #94a3b8;
  user-select: none;
}
.cfg-json-err-caret code {
  color: #dc2626;
  font-weight: 700;
  line-height: 1;
}

@media (max-width: 768px) {
  .cfg-page { padding: 0; }
  .cfg-editor { padding: 12px; }
  .cfg-mode-bar { flex-wrap: wrap; gap: 8px; }
  .cfg-cats {
    overflow-x: auto;
    flex-wrap: nowrap;
    padding-bottom: 4px;
  }
  .cfg-cat-btn {
    flex-shrink: 0;
    font-size: 12px;
    padding: 6px 10px;
  }
  .cfg-field-row { padding: 8px 0; }
  .cfg-json-panel { padding: 0; }
  .cfg-json-editor { font-size: 12px; min-height: 300px; }
  .cfg-search-bar { width: 100%; }
}
</style>
