<template>
  <div class="pje-root">
    <template v-for="key in Object.keys(data)" :key="key">

      <!-- ── BOOLEAN ── -->
      <div v-if="typeOf(data[key]) === 'bool'" class="pje-row pje-row-bool">
        <span class="pje-key">{{ key }}</span>
        <label class="pje-toggle">
          <input type="checkbox" :checked="data[key]" @change="set(key, $event.target.checked)" />
          <span class="pje-toggle-track"><span class="pje-toggle-thumb"></span></span>
        </label>
        <span class="pje-bool-badge" :class="data[key] ? 'pje-bool-on' : 'pje-bool-off'">
          {{ data[key] ? '开启' : '关闭' }}
        </span>
      </div>

      <!-- ── NUMBER ── -->
      <div v-else-if="typeOf(data[key]) === 'num'" class="pje-row">
        <span class="pje-key" :title="key">{{ key }}</span>
        <input type="number" class="pje-input pje-num-input"
          :value="data[key]"
          :step="isFloat(data[key]) ? 'any' : 1"
          @change="set(key, toNum($event.target.value, data[key]))"
        />
      </div>

      <!-- ── STRING ── -->
      <div v-else-if="typeOf(data[key]) === 'str'" class="pje-row">
        <span class="pje-key" :title="key">{{ key }}</span>
        <input type="text" class="pje-input pje-str-input"
          :value="data[key]"
          @input="set(key, $event.target.value)"
        />
      </div>

      <!-- ── NULL ── -->
      <div v-else-if="typeOf(data[key]) === 'null'" class="pje-row">
        <span class="pje-key" :title="key">{{ key }}</span>
        <span class="pje-null-tag">null</span>
      </div>

      <!-- ── PRIMITIVE ARRAY ── -->
      <div v-else-if="typeOf(data[key]) === 'arr-prim'" class="pje-row pje-row-block">
        <div class="pje-key pje-key-block">{{ key }}</div>
        <div class="pje-arr-wrap">
          <div v-for="(item, i) in data[key]" :key="i" class="pje-arr-item">
            <input
              :type="typeof item === 'number' ? 'number' : 'text'"
              class="pje-input pje-arr-input"
              :value="typeof item === 'boolean' ? String(item) : item"
              @change="setArrItem(key, i, $event.target.value)"
            />
            <button class="pje-del-btn" @click="removeArrItem(key, i)" title="删除">✕</button>
          </div>
          <div v-if="data[key].length === 0" class="pje-empty-hint">暂无元素</div>
          <button class="pje-add-btn" @click="addArrItem(key)">+ 添加</button>
        </div>
      </div>

      <!-- ── DICT-LIKE OBJECT ── -->
      <div v-else-if="typeOf(data[key]) === 'dict'" class="pje-row pje-row-block">
        <div class="pje-key pje-key-block">{{ key }}</div>
        <div class="pje-dict-wrap">
          <!-- Table header -->
          <div class="pje-dict-head">
            <span class="pje-dict-th pje-dict-th-key">键名</span>
            <span v-for="col in getDictCols(data[key])" :key="col" class="pje-dict-th">{{ col }}</span>
            <span class="pje-dict-th pje-dict-th-del"></span>
          </div>
          <!-- Rows -->
          <div v-for="eKey in Object.keys(data[key])" :key="eKey" class="pje-dict-row">
            <input class="pje-input pje-dict-key-input" :value="eKey"
              @blur="renameDictKey(key, eKey, $event.target.value)" placeholder="键名" />
            <!-- Sub-object columns -->
            <template v-if="typeof data[key][eKey] === 'object' && data[key][eKey] !== null && !Array.isArray(data[key][eKey])">
              <template v-for="col in getDictCols(data[key])" :key="col">
                <div v-if="typeof data[key][eKey][col] === 'boolean'" class="pje-dict-bool-cell">
                  <label class="pje-toggle pje-toggle-sm">
                    <input type="checkbox" :checked="data[key][eKey][col]"
                      @change="setDictSubValBool(key, eKey, col, $event.target.checked)" />
                    <span class="pje-toggle-track"><span class="pje-toggle-thumb"></span></span>
                  </label>
                </div>
                <input v-else class="pje-input pje-dict-val-input"
                  :type="typeof data[key][eKey][col] === 'number' ? 'number' : 'text'"
                  :value="data[key][eKey][col]"
                  @change="setDictSubVal(key, eKey, col, $event.target.value)"
                />
              </template>
            </template>
            <!-- Primitive value (no sub-keys) -->
            <template v-else>
              <input class="pje-input pje-dict-val-input pje-dict-prim-full"
                :type="typeof data[key][eKey] === 'number' ? 'number' : 'text'"
                :value="data[key][eKey]"
                @change="setDictPrimVal(key, eKey, $event.target.value)"
              />
            </template>
            <button class="pje-del-btn" @click="removeDictEntry(key, eKey)">✕</button>
          </div>
          <div v-if="Object.keys(data[key]).length === 0" class="pje-empty-hint">暂无条目</div>
          <button class="pje-add-btn" @click="addDictEntry(key)">+ 添加</button>
        </div>
      </div>

      <!-- ── NESTED OBJECT (recursive, collapsible) ── -->
      <div v-else-if="typeOf(data[key]) === 'obj'" class="pje-row pje-row-block pje-nested-block">
        <div class="pje-key pje-key-collapsible" @click="toggleExpand(key)">
          <svg class="pje-caret" :style="{ transform: isExpanded(key) ? 'rotate(90deg)' : 'none' }"
            viewBox="0 0 12 12" fill="currentColor">
            <path d="M4 2l5 4-5 4V2z"/>
          </svg>
          {{ key }}
          <span class="pje-obj-hint">{{ objectHint(data[key]) }}</span>
        </div>
        <div v-if="isExpanded(key)" class="pje-nested-body">
          <PluginJsonEditor :data="data[key]" :depth="depth + 1" @change="v => set(key, v)" />
        </div>
      </div>

      <!-- ── FALLBACK: array of objects or other complex types ── -->
      <div v-else class="pje-row pje-row-block">
        <div class="pje-key pje-key-block">{{ key }}</div>
        <textarea class="pje-json-ta" rows="4" spellcheck="false"
          :value="JSON.stringify(data[key], null, 2)"
          @input="setJson(key, $event.target.value)"
        ></textarea>
      </div>

    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

defineOptions({ name: 'PluginJsonEditor' })

const props = defineProps({
  data:  { type: Object, required: true },
  depth: { type: Number, default: 0 },
})
const emit = defineEmits(['change'])

function set(key, val) {
  emit('change', { ...props.data, [key]: val })
}

// ── Type detection ─────────────────────────────────────────────────────
function typeOf(v) {
  if (v === null)             return 'null'
  if (typeof v === 'boolean') return 'bool'
  if (typeof v === 'number')  return 'num'
  if (typeof v === 'string')  return 'str'
  if (Array.isArray(v)) {
    if (v.length === 0 || v.every(x => x === null || typeof x !== 'object')) return 'arr-prim'
    return 'arr-obj'
  }
  if (isDictLike(v)) return 'dict'
  return 'obj'
}

// Dict-like: all values are non-null objects with the same key set
function isDictLike(obj) {
  const vals = Object.values(obj)
  if (vals.length === 0) return false
  if (!vals.every(v => typeof v === 'object' && v !== null && !Array.isArray(v))) return false
  const keySets = vals.map(v => JSON.stringify(Object.keys(v).sort()))
  return new Set(keySets).size === 1
}

function isFloat(n) { return n !== Math.floor(n) }

function toNum(s, orig) {
  const n = String(s).includes('.') ? parseFloat(s) : parseInt(s, 10)
  return isNaN(n) ? orig : n
}

// ── Array ops ──────────────────────────────────────────────────────────
function setArrItem(key, i, rawVal) {
  const arr    = [...props.data[key]]
  const sample = arr[i]
  arr[i] = typeof sample === 'number' ? toNum(rawVal, sample)
         : typeof sample === 'boolean' ? rawVal === 'true'
         : rawVal
  set(key, arr)
}

function removeArrItem(key, i) {
  set(key, props.data[key].filter((_, idx) => idx !== i))
}

function addArrItem(key) {
  const arr    = props.data[key]
  const sample = arr[0]
  const newItem = typeof sample === 'number' ? 0
               : typeof sample === 'boolean' ? false
               : ''
  set(key, [...arr, newItem])
}

// ── Dict ops ───────────────────────────────────────────────────────────
function getDictCols(obj) {
  const vals = Object.values(obj)
  if (!vals.length) return []
  const fv = vals[0]
  if (typeof fv !== 'object' || fv === null) return []
  return Object.keys(fv)
}

function renameDictKey(parentKey, oldKey, newKey) {
  const trimmed = newKey.trim()
  if (trimmed === oldKey || !trimmed) return
  const src    = props.data[parentKey]
  const newObj = {}
  for (const [k, v] of Object.entries(src)) newObj[k === oldKey ? trimmed : k] = v
  set(parentKey, newObj)
}

function setDictSubVal(parentKey, entryKey, col, rawVal) {
  const origVal = props.data[parentKey][entryKey][col]
  const newVal  = typeof origVal === 'number' ? toNum(rawVal, origVal) : rawVal
  const src     = props.data[parentKey]
  set(parentKey, { ...src, [entryKey]: { ...src[entryKey], [col]: newVal } })
}

function setDictSubValBool(parentKey, entryKey, col, checked) {
  const src = props.data[parentKey]
  set(parentKey, { ...src, [entryKey]: { ...src[entryKey], [col]: checked } })
}

function setDictPrimVal(parentKey, entryKey, rawVal) {
  const orig   = props.data[parentKey][entryKey]
  const newVal = typeof orig === 'number' ? toNum(rawVal, orig) : rawVal
  set(parentKey, { ...props.data[parentKey], [entryKey]: newVal })
}

function removeDictEntry(parentKey, entryKey) {
  const src = { ...props.data[parentKey] }
  delete src[entryKey]
  set(parentKey, src)
}

function addDictEntry(parentKey) {
  const src  = props.data[parentKey]
  const vals = Object.values(src)
  const template = vals.length > 0
    ? Object.fromEntries(Object.keys(vals[0]).map(k => {
        const sv = vals[0][k]
        return [k, typeof sv === 'number' ? 0 : typeof sv === 'boolean' ? false : '']
      }))
    : {}
  let newKey = '新条目', i = 1
  while (newKey in src) newKey = `新条目${i++}`
  set(parentKey, { ...src, [newKey]: template })
}

// ── Expand / collapse ──────────────────────────────────────────────────
const expandedKeys = ref(new Set())
function isExpanded(key)  { return expandedKeys.value.has(key) }
function toggleExpand(key) {
  const s = new Set(expandedKeys.value)
  s.has(key) ? s.delete(key) : s.add(key)
  expandedKeys.value = s
}

function objectHint(obj) {
  const keys = Object.keys(obj)
  if (!keys.length) return '(空)'
  return `{ ${keys.slice(0, 3).join(', ')}${keys.length > 3 ? ', …' : ''} }`
}

// Auto-expand all nested-object fields at root depth
onMounted(() => {
  if (props.depth === 0) {
    const toExpand = Object.keys(props.data).filter(k => typeOf(props.data[k]) === 'obj')
    expandedKeys.value = new Set(toExpand)
  }
})

// ── JSON fallback textarea ─────────────────────────────────────────────
function setJson(key, text) {
  try { set(key, JSON.parse(text)) } catch { /* ignore parse errors */ }
}
</script>

<style scoped>
/* ── Root ── */
.pje-root {
  display: flex; flex-direction: column; gap: 1px;
}

/* ── Row ── */
.pje-row {
  display: flex; align-items: center; gap: 10px;
  padding: 4px 10px; min-height: 34px; border-radius: 6px;
  transition: background .1s;
}
.pje-row:hover { background: #f8fafc; }
.pje-row-block { flex-direction: column; align-items: flex-start; gap: 5px; padding-top: 6px; padding-bottom: 6px; }

/* ── Key label ── */
.pje-key {
  font-size: 12.5px; font-weight: 500; color: #374151;
  min-width: 170px; max-width: 260px; flex-shrink: 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  font-family: 'SFMono-Regular', Consolas, monospace;
}
.pje-key-block  { min-width: unset; max-width: unset; font-size: 13px; }

/* ── Collapsible key ── */
.pje-key-collapsible {
  display: flex; align-items: center; gap: 6px;
  cursor: pointer; user-select: none;
  font-size: 13px; font-weight: 600; color: #1e293b;
  padding: 2px 0;
}
.pje-key-collapsible:hover { color: #3b82f6; }
.pje-obj-hint { font-size: 11px; color: #94a3b8; font-weight: 400; font-family: monospace; margin-left: 2px; }

/* ── Caret ── */
.pje-caret {
  width: 12px; height: 12px; flex-shrink: 0; color: #9ca3af; transition: transform .15s;
}

/* ── Nested body ── */
.pje-nested-block { padding-bottom: 4px; }
.pje-nested-body {
  padding-left: 14px; border-left: 2px solid #e2e8f0;
  margin-left: 6px; margin-top: 2px;
}

/* ── Inputs ── */
.pje-input {
  border: 1px solid #e2e8f0; border-radius: 6px;
  padding: 5px 8px; font-size: 12.5px; color: #1e293b;
  outline: none; background: #fff; transition: border-color .15s;
}
.pje-input:focus { border-color: #3b82f6; }
.pje-num-input  { width: 110px; }
.pje-str-input  { flex: 1; min-width: 140px; max-width: 420px; }

/* ── Boolean ── */
.pje-row-bool  { cursor: default; }
.pje-toggle { display: inline-flex; align-items: center; cursor: pointer; user-select: none; flex-shrink: 0; }
.pje-toggle input { position: absolute; opacity: 0; width: 0; height: 0; }
.pje-toggle-track { position: relative; width: 40px; height: 22px; background: #e2e8f0; border-radius: 11px; transition: background 0.2s; }
.pje-toggle input:checked + .pje-toggle-track { background: #3b82f6; }
.pje-toggle-thumb { position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; background: #fff; border-radius: 50%; transition: transform 0.2s; box-shadow: 0 1px 3px rgba(0,0,0,0.15); }
.pje-toggle input:checked + .pje-toggle-track .pje-toggle-thumb { transform: translateX(18px); }
.pje-toggle-sm .pje-toggle-track { width: 34px; height: 18px; border-radius: 9px; }
.pje-toggle-sm .pje-toggle-thumb { width: 12px; height: 12px; }
.pje-toggle-sm input:checked + .pje-toggle-track .pje-toggle-thumb { transform: translateX(16px); }
.pje-bool-badge { font-size: 11px; border-radius: 4px; padding: 1px 7px; }
.pje-bool-on  { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.pje-bool-off { background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0; }

/* ── Null ── */
.pje-null-tag {
  font-size: 12px; color: #9ca3af; background: #f9fafb;
  border: 1px solid #e5e7eb; border-radius: 4px; padding: 2px 8px;
  font-family: monospace;
}

/* ── Primitive array ── */
.pje-arr-wrap { display: flex; flex-direction: column; gap: 4px; width: 100%; padding-left: 6px; }
.pje-arr-item { display: flex; align-items: center; gap: 6px; }
.pje-arr-input { flex: 1; max-width: 360px; }
.pje-empty-hint { font-size: 12px; color: #94a3b8; padding: 3px 0; }

/* ── Buttons ── */
.pje-del-btn {
  background: none; border: 1px solid #fca5a5; color: #ef4444; border-radius: 5px;
  padding: 3px 7px; font-size: 12px; cursor: pointer; line-height: 1; flex-shrink: 0;
}
.pje-del-btn:hover { background: #fef2f2; }
.pje-add-btn {
  background: none; border: 1px dashed #93c5fd; color: #3b82f6; border-radius: 5px;
  padding: 4px 12px; font-size: 12px; cursor: pointer; margin-top: 3px; width: fit-content;
}
.pje-add-btn:hover { background: #eff6ff; }

/* ── Dict table ── */
.pje-dict-wrap { width: 100%; padding-left: 6px; overflow-x: auto; }
.pje-dict-head {
  display: flex; gap: 4px; padding: 4px 6px;
  font-size: 11px; font-weight: 600; color: #64748b;
  text-transform: uppercase; letter-spacing: .04em;
  border-bottom: 1px solid #e2e8f0;
}
.pje-dict-th        { flex: 1; min-width: 80px; }
.pje-dict-th-key    { flex: 0 0 130px; }
.pje-dict-th-del    { flex: 0 0 34px; }

.pje-dict-row {
  display: flex; align-items: center; gap: 4px;
  padding: 3px 0; border-bottom: 1px solid #f8fafc;
}
.pje-dict-key-input    { flex: 0 0 130px; font-size: 12px; padding: 4px 7px; }
.pje-dict-val-input    { flex: 1; min-width: 80px; font-size: 12px; padding: 4px 7px; }
.pje-dict-prim-full    { flex: 2; }
.pje-dict-bool-cell    { display: flex; align-items: center; justify-content: center; flex: 1; min-width: 80px; }

/* ── JSON fallback ── */
.pje-json-ta {
  width: 100%; max-width: 600px; box-sizing: border-box;
  border: 1px solid #e2e8f0; border-radius: 6px;
  padding: 8px 10px; font-size: 12px; line-height: 1.5;
  font-family: 'SFMono-Regular', Consolas, monospace; color: #1e293b;
  background: #fafafa; resize: vertical; outline: none;
}
.pje-json-ta:focus { border-color: #3b82f6; }
</style>
