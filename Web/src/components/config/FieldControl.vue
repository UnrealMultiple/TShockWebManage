<template>
  <div class="fc-row" :class="'fc-type-' + field.type">
    <!-- 字段信息（左侧） -->
    <div class="fc-info">
      <span class="fc-key">{{ field.key }}</span>
      <span class="fc-desc">{{ normalizedDescription }}</span>
    </div>
    <!-- 控件（右侧） -->
    <div class="fc-ctrl">

      <!-- Boolean → 开关 -->
      <label v-if="field.type === 'boolean'" class="fc-toggle">
        <input type="checkbox" :checked="!!modelValue" @change="emit('update:modelValue', $event.target.checked)" />
        <span class="fc-toggle-track">
          <span class="fc-toggle-thumb"></span>
        </span>
        <span class="fc-toggle-label">{{ modelValue ? '开启' : '关闭' }}</span>
      </label>

      <!-- Number → 数字输入 -->
      <input v-else-if="field.type === 'number'"
        type="number"
        class="fc-input fc-input-num"
        :value="modelValue"
        @change="emit('update:modelValue', parseNum($event.target.value))"
      />

      <!-- Select → 下拉框 -->
      <select v-else-if="field.type === 'select'"
        class="fc-select"
        :value="modelValue"
        @change="emit('update:modelValue', $event.target.value)">
        <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
      </select>

      <!-- Color → 颜色选取器（RGB 数组 ↔ #rrggbb） -->
      <div v-else-if="field.type === 'color'" class="fc-color-wrap">
        <input type="color"
          class="fc-color-input"
          :value="rgbToHex(modelValue)"
          @input="emit('update:modelValue', hexToRgb($event.target.value))"
        />
        <span class="fc-color-preview" :style="{ background: rgbToHex(modelValue) }"></span>
        <span class="fc-color-text">{{ formatRgb(modelValue) }}</span>
      </div>

      <!-- rest_tokens → ApplicationRestTokens 编辑器（Token名 / 用户名 / 用户组） -->
      <div v-else-if="field.type === 'rest_tokens'" class="fc-dict">
        <div class="fc-dict-head">
          <span>Token 名称</span><span>用户名</span><span>用户组</span><span></span>
        </div>
        <div v-for="(entry, idx) in dictEntries" :key="idx" class="fc-dict-row">
          <input class="fc-input fc-dict-key" placeholder="Token 名称"
            :value="entry.k" @input="updateDictKey(idx, $event.target.value)" />
          <input class="fc-input fc-dict-user" placeholder="用户名"
            :value="entry.v.Username" @input="updateDictField(idx, 'Username', $event.target.value)" />
          <input class="fc-input fc-dict-group" placeholder="用户组"
            :value="entry.v.UserGroupName" @input="updateDictField(idx, 'UserGroupName', $event.target.value)" />
          <button class="fc-dict-del" @click="removeDictEntry(idx)" title="删除">✕</button>
        </div>
        <div v-if="dictEntries.length === 0" class="fc-ilist-empty">暂无 Token，点击下方按钮添加</div>
        <button class="fc-dict-add" @click="addDictEntry">+ 添加 Token</button>
      </div>

      <!-- item_list → 初始物品栏编辑器（netID / prefix / stack） -->
      <div v-else-if="field.type === 'item_list'" class="fc-ilist">
        <div class="fc-ilist-head">
          <span>物品ID</span><span>前缀</span><span>数量</span><span></span>
        </div>
        <div v-for="(item, idx) in itemListEntries" :key="idx" class="fc-ilist-row">
          <input class="fc-input fc-ilist-cell" type="number" placeholder="0"
            :value="item.netID" @change="updateItem(idx, 'netID', parseNum($event.target.value))" />
          <input class="fc-input fc-ilist-cell" type="number" placeholder="0"
            :value="item.prefix" @change="updateItem(idx, 'prefix', parseNum($event.target.value))" />
          <input class="fc-input fc-ilist-cell" type="number" placeholder="1"
            :value="item.stack" @change="updateItem(idx, 'stack', parseNum($event.target.value))" />
          <button class="fc-dict-del" @click="removeItem(idx)" title="删除">✕</button>
        </div>
        <div v-if="itemListEntries.length === 0" class="fc-ilist-empty">暂无物品，点击下方按钮添加</div>
        <button class="fc-dict-add" @click="addItem">+ 添加物品</button>
      </div>

      <!-- JSON → 多行文本域 -->
      <div v-else-if="field.type === 'json'" class="fc-json-wrap">
        <textarea class="fc-json-area"
          :value="jsonText"
          @input="onJsonInput($event.target.value)"
          rows="6"
          placeholder="[]"
          spellcheck="false"
        ></textarea>
        <span v-if="jsonError" class="fc-json-err">{{ jsonError }}</span>
      </div>

      <!-- String → 文本输入 -->
      <input v-else
        type="text"
        class="fc-input fc-input-str"
        :value="modelValue"
        @input="emit('update:modelValue', $event.target.value)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  field:      { type: Object,  required: true },
  modelValue: { required: true },
})
const emit = defineEmits(['update:modelValue'])

const normalizedDescription = computed(() => {
  const raw = String(props.field?.description ?? '').trim()
  if (!raw) return ''

  // 兼容 schema 中拼接的元信息，仅保留主描述。
  const main = raw.split(' * **字段类型**:')[0]?.trim() || raw
  return main
    .replace(/\*\*/g, '')
    .replace(/`/g, '')
    .replace(/\s+/g, ' ')
    .trim()
})

// ── Number 解析 ────────────────────────────────────────────────────
function parseNum(v) {
  const n = v.includes('.') ? parseFloat(v) : parseInt(v, 10)
  return isNaN(n) ? 0 : n
}

// ── Color 工具 ─────────────────────────────────────────────────────
function rgbToHex(arr) {
  if (!Array.isArray(arr) || arr.length < 3) return '#ffffff'
  return '#' + arr.slice(0, 3).map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('')
}
function hexToRgb(hex) {
  if (!/^#[0-9a-f]{6}$/i.test(hex)) return [255, 255, 255]
  return [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)]
}
function formatRgb(arr) {
  if (!Array.isArray(arr) || arr.length < 3) return 'rgb(255,255,255)'
  return `rgb(${arr[0]}, ${arr[1]}, ${arr[2]})`
}

// ── Dict 工具 ──────────────────────────────────────────────────────
const dictEntries = computed(() => {
  const v = props.modelValue
  if (!v || typeof v !== 'object' || Array.isArray(v)) return []
  return Object.entries(v).map(([k, val]) => ({
    k,
    v: { Username: val?.Username ?? '', UserGroupName: val?.UserGroupName ?? '' }
  }))
})

function emitDict(entries) {
  const obj = {}
  // 允许空 key 条目暂存（用于新增时输入过程），保存时由外层过滤
  for (const e of entries) {
    obj[e.k] = { Username: e.v.Username, UserGroupName: e.v.UserGroupName }
  }
  emit('update:modelValue', obj)
}
function addDictEntry() {
  const entries = [...dictEntries.value, { k: '', v: { Username: '', UserGroupName: '' } }]
  emitDict(entries)
}
function removeDictEntry(idx) {
  const entries = dictEntries.value.filter((_, i) => i !== idx)
  emitDict(entries)
}
function updateDictKey(idx, newKey) {
  const entries = dictEntries.value.map((e, i) => i === idx ? { ...e, k: newKey } : e)
  emitDict(entries)
}
function updateDictField(idx, field, val) {
  const entries = dictEntries.value.map((e, i) =>
    i === idx ? { ...e, v: { ...e.v, [field]: val } } : e
  )
  emitDict(entries)
}

// ── item_list 工具 ────────────────────────────────────────────────
const itemListEntries = computed(() => {
  const v = props.modelValue
  if (!Array.isArray(v)) return []
  // TShock 使用 netID（大写），兼容 netId 写法
  return v.map(i => ({
    netID:  i?.netID  ?? i?.netId  ?? 0,
    prefix: i?.prefix ?? 0,
    stack:  i?.stack  ?? 1,
  }))
})
function emitItemList(entries) {
  // 写回时使用 TShock 标准字段名 netID
  emit('update:modelValue', entries.map(e => ({ netID: e.netID, prefix: e.prefix, stack: e.stack })))
}
function addItem() {
  emitItemList([...itemListEntries.value, { netID: 0, prefix: 0, stack: 1 }])
}
function removeItem(idx) {
  emitItemList(itemListEntries.value.filter((_, i) => i !== idx))
}
function updateItem(idx, fld, val) {
  emitItemList(itemListEntries.value.map((e, i) => i === idx ? { ...e, [fld]: val } : e))
}

// ── JSON 工具 ──────────────────────────────────────────────────────
const jsonText  = ref('')
const jsonError = ref('')

watch(() => props.modelValue, (val) => {
  if (props.field.type !== 'json') return
  try {
    const candidate = JSON.stringify(val, null, 2)
    if (jsonText.value !== candidate) jsonText.value = candidate
  } catch { jsonText.value = '[]' }
}, { immediate: true })

function onJsonInput(text) {
  jsonText.value = text
  try {
    const parsed = JSON.parse(text)
    jsonError.value = ''
    emit('update:modelValue', parsed)
  } catch (e) {
    jsonError.value = `JSON 格式错误: ${e.message}`
  }
}
</script>

<style scoped>
/* ── 行容器 ── */
.fc-row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 12px 16px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #f1f5f9;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.fc-row:hover { border-color: #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }

/* 字段信息 */
.fc-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding-top: 2px;
}
.fc-key {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  font-family: 'SFMono-Regular', Consolas, monospace;
  word-break: break-all;
}
.fc-desc {
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
}

/* 控件区 */
.fc-ctrl {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  min-width: 180px;
  max-width: 320px;
}

/* ── 通用输入框 ── */
.fc-input {
  border: 1px solid #e2e8f0;
  border-radius: 7px;
  padding: 7px 11px;
  font-size: 13px;
  outline: none;
  color: #1e293b;
  background: #fff;
  transition: border-color 0.15s;
  width: 100%;
}
.fc-input:focus { border-color: #3b82f6; }
.fc-input-num   { width: 110px; text-align: right; }
.fc-input-str   { width: 240px; }

/* ── Select ── */
.fc-select {
  border: 1px solid #e2e8f0;
  border-radius: 7px;
  padding: 7px 28px 7px 11px;
  font-size: 13px;
  outline: none;
  color: #1e293b;
  background: #fff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E") no-repeat right 8px center / 16px;
  appearance: none;
  cursor: pointer;
  transition: border-color 0.15s;
  width: 100%;
  max-width: 200px;
}
.fc-select:focus { border-color: #3b82f6; }

/* ── Toggle 开关 ── */
.fc-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}
.fc-toggle input { position: absolute; opacity: 0; width: 0; height: 0; }
.fc-toggle-track {
  position: relative;
  width: 40px;
  height: 22px;
  background: #e2e8f0;
  border-radius: 11px;
  transition: background 0.2s;
}
.fc-toggle input:checked + .fc-toggle-track { background: #3b82f6; }
.fc-toggle-thumb {
  position: absolute;
  top: 3px; left: 3px;
  width: 16px; height: 16px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}
.fc-toggle input:checked + .fc-toggle-track .fc-toggle-thumb { transform: translateX(18px); }
.fc-toggle-label { font-size: 12px; color: #64748b; width: 28px; }

/* ── Color ── */
.fc-color-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}
.fc-color-input {
  width: 36px; height: 36px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 2px;
  cursor: pointer;
  background: none;
}
.fc-color-preview {
  width: 24px; height: 24px;
  border-radius: 50%;
  border: 1px solid #e2e8f0;
  flex-shrink: 0;
}
.fc-color-text {
  font-size: 12px;
  color: #64748b;
  font-family: monospace;
  white-space: nowrap;
}

/* ── Dict (rest_tokens) ── */
.fc-dict   { display: flex; flex-direction: column; gap: 6px; width: 100%; }
.fc-dict-head {
  display: grid; grid-template-columns: 2fr 1.5fr 1.5fr 32px;
  gap: 5px; padding: 0 2px;
  font-size: 11px; color: #94a3b8; font-weight: 600; letter-spacing: 0.03em;
  text-transform: uppercase;
}
.fc-dict-row {
  display: grid; grid-template-columns: 2fr 1.5fr 1.5fr 32px;
  gap: 5px; align-items: center;
}
.fc-dict-key   { font-family: monospace; width: 100%; min-width: 0; }
.fc-dict-user  { width: 100%; min-width: 0; }
.fc-dict-group { width: 100%; min-width: 0; }
.fc-dict-del {
  background: none; border: 1px solid #e2e8f0; border-radius: 6px;
  padding: 4px 8px; cursor: pointer; color: #94a3b8; font-size: 12px;
  transition: all 0.15s;
}
.fc-dict-del:hover { background: #fee2e2; border-color: #fca5a5; color: #dc2626; }
.fc-dict-add {
  align-self: flex-start;
  background: none; border: 1px dashed #94a3b8; border-radius: 7px;
  padding: 5px 12px; font-size: 12px; color: #64748b;
  cursor: pointer; transition: all 0.15s; margin-top: 2px;
}
.fc-dict-add:hover { border-color: #3b82f6; color: #3b82f6; background: #eff6ff; }

/* ── JSON ── */
.fc-json-wrap { display: flex; flex-direction: column; gap: 4px; width: 100%; }
.fc-json-area {
  border: 1px solid #e2e8f0; border-radius: 7px;
  padding: 8px 10px; font-size: 12px;
  font-family: 'SFMono-Regular', Consolas, monospace;
  resize: vertical; outline: none; color: #1e293b;
  background: #f8fafc; line-height: 1.5;
  min-width: 280px;
  transition: border-color 0.15s;
}
.fc-json-area:focus { border-color: #3b82f6; }
.fc-json-err { font-size: 11px; color: #dc2626; }

/* ── item_list ── */
.fc-ilist { display: flex; flex-direction: column; gap: 6px; width: 100%; }
.fc-ilist-head {
  display: grid; grid-template-columns: 1fr 1fr 1fr 32px;
  gap: 5px; padding: 0 2px;
  font-size: 11px; color: #94a3b8; font-weight: 600; letter-spacing: 0.03em;
  text-transform: uppercase;
}
.fc-ilist-row { display: grid; grid-template-columns: 1fr 1fr 1fr 32px; gap: 5px; align-items: center; }
.fc-ilist-cell { text-align: right; width: 100%; min-width: 0; }
.fc-ilist-empty { font-size: 12px; color: #94a3b8; text-align: center; padding: 8px 0; }

/* rest_tokens / item_list / json 类型 ctrl 区不限制宽度 */
.fc-type-rest_tokens .fc-ctrl,
.fc-type-item_list .fc-ctrl,
.fc-type-json .fc-ctrl {
  max-width: none;
  width: 100%;
}
.fc-type-rest_tokens,
.fc-type-item_list,
.fc-type-json {
  flex-direction: column;
  align-items: stretch;
}
.fc-type-rest_tokens .fc-info,
.fc-type-item_list .fc-info,
.fc-type-json .fc-info {
  margin-bottom: 8px;
}

@media (max-width: 768px) {
  .fc-row { flex-direction: column; gap: 8px; padding: 10px 12px; }
  .fc-ctrl { min-width: 0; max-width: none; width: 100%; }
  .fc-input-str { width: 100%; box-sizing: border-box; }
  .fc-input-num { width: 100%; max-width: 160px; box-sizing: border-box; }
  .fc-select { max-width: 100%; }
  .fc-dict-head, .fc-dict-row { grid-template-columns: 1.5fr 1fr 1fr 28px; gap: 3px; font-size: 10px; }
  .fc-ilist-head, .fc-ilist-row { grid-template-columns: 1fr 1fr 1fr 28px; gap: 3px; font-size: 10px; }
  .fc-json-area { min-width: 0; width: 100%; box-sizing: border-box; }
}
</style>
