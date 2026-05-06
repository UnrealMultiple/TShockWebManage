<template>
  <!-- 背包查看/编辑模态框 -->
  <transition name="inv-fade">
    <div v-if="show" class="inv-overlay" @click.self="$emit('close')">
      <div class="inv-panel">

        <!-- ── 标题栏 ──────────────────────────────── -->
        <div class="inv-header">
          <div class="inv-header-left">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="inv-icon"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg>
            <span class="inv-title">{{ username }} 的背包</span>
            <span v-if="isOnline" class="online-badge">在线</span>
            <span v-else class="offline-badge">离线</span>
          </div>
          <div class="inv-header-right">
            <span class="inv-stat">❤ {{ health }}/{{ maxHealth }}</span>
            <span class="inv-stat">✦ {{ mana }}/{{ maxMana }}</span>
            <button class="inv-close-btn" @click="$emit('close')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="16" height="16"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
        </div>

        <!-- 在线警告 -->
        <div v-if="isOnline" class="inv-warn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          玩家当前在线，修改可能有延迟或需重进游戏后完全生效
        </div>

        <!-- 基础属性（整合到背包修改） -->
        <div v-if="canEdit" class="inv-stat-edit">
          <div class="inv-stat-edit-title">基础属性（SSC）</div>
          <div class="inv-stat-edit-row">
            <label>血量上限</label>
            <input type="number" min="1" max="500" v-model.number="editMaxHealth" class="inv-input" />
            <label>魔力上限</label>
            <input type="number" min="0" max="200" v-model.number="editMaxMana" class="inv-input" />
          </div>

          <div class="inv-stat-edit-title" style="margin-top:16px;">永久增益物品</div>
          <div class="inv-buff-grid">
            <label class="inv-buff-toggle">
              <input type="checkbox" v-model="editExtraSlot" />
              <span>恶魔之心 (饰品栏+1)</span>
            </label>
            <label class="inv-buff-toggle">
              <input type="checkbox" v-model="editUnlockedBiomeTorches" />
              <span>火把神徽章</span>
            </label>
            <label class="inv-buff-toggle">
              <input type="checkbox" v-model="editAteArtisanBread" />
              <span>工匠面包</span>
            </label>
            <label class="inv-buff-toggle">
              <input type="checkbox" v-model="editUsedAegisCrystal" />
              <span>生命水晶 (活力辐射)</span>
            </label>
            <label class="inv-buff-toggle">
              <input type="checkbox" v-model="editUsedAegisFruit" />
              <span>埃癸斯果 (防御+4)</span>
            </label>
            <label class="inv-buff-toggle">
              <input type="checkbox" v-model="editUsedArcaneCrystal" />
              <span>奥术水晶 (魔力恢复)</span>
            </label>
            <label class="inv-buff-toggle">
              <input type="checkbox" v-model="editUsedGalaxyPearl" />
              <span>银河珍珠 (运气+0.03)</span>
            </label>
            <label class="inv-buff-toggle">
              <input type="checkbox" v-model="editUsedGummyWorm" />
              <span>黏性蠕虫 (渔力+3)</span>
            </label>
            <label class="inv-buff-toggle">
              <input type="checkbox" v-model="editUsedAmbrosia" />
              <span>珍馐 (挖矿/建造+5%)</span>
            </label>
            <label class="inv-buff-toggle">
              <input type="checkbox" v-model="editUnlockedSuperCart" />
              <span>矿车升级包</span>
            </label>
          </div>
        </div>

        <!-- ── 分区 Tab ──────────────────────────────── -->
        <div class="inv-tabs">
          <button v-for="t in TABS" :key="t.id"
            :class="['inv-tab', { active: activeTab === t.id }]"
            @click="activeTab = t.id; selectedSlot = null">
            {{ t.label }}
          </button>
        </div>

        <!-- ── 内容区 ──────────────────────────────── -->
        <div v-if="loading" class="inv-loading">加载背包数据中…</div>
        <div v-else-if="error" class="inv-error">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          {{ error }}
        </div>
        <div v-else class="inv-body">
          <!-- 主背包 -->
          <template v-if="activeTab === 'main'">
            <div class="inv-section-label">快捷栏（0–9）</div>
            <div class="inv-grid row-10">
              <div v-for="slot in slotRange(0, 9)" :key="slot.index"
                class="inv-slot" :class="slotClass(slot)"
                @click="toggleEdit(slot)">
                <item-slot :item="slot" />
              </div>
            </div>
            <div class="inv-section-label">背包（10–49）</div>
            <div class="inv-grid row-10">
              <div v-for="slot in slotRange(10, 49)" :key="slot.index"
                class="inv-slot" :class="slotClass(slot)"
                @click="toggleEdit(slot)">
                <item-slot :item="slot" />
              </div>
            </div>
            <div class="inv-row-pair">
              <div>
                <div class="inv-section-label">硬币（50–53）</div>
                <div class="inv-grid row-4">
                  <div v-for="slot in slotRange(50, 53)" :key="slot.index"
                    class="inv-slot" :class="slotClass(slot)" @click="toggleEdit(slot)">
                    <item-slot :item="slot" />
                  </div>
                </div>
              </div>
              <div>
                <div class="inv-section-label">弹药（54–57）</div>
                <div class="inv-grid row-4">
                  <div v-for="slot in slotRange(54, 57)" :key="slot.index"
                    class="inv-slot" :class="slotClass(slot)" @click="toggleEdit(slot)">
                    <item-slot :item="slot" />
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- 防具/饰品 -->
          <template v-if="activeTab === 'armor'">
            <div class="inv-row-pair">
              <div>
                <div class="inv-section-label">防具（59–61）</div>
                <div class="inv-grid row-3">
                  <div v-for="slot in slotRange(59, 61)" :key="slot.index"
                    class="inv-slot" :class="slotClass(slot)" @click="toggleEdit(slot)">
                    <item-slot :item="slot" />
                  </div>
                </div>
              </div>
              <div>
                <div class="inv-section-label">时装防具（69–71）</div>
                <div class="inv-grid row-3">
                  <div v-for="slot in slotRange(69, 71)" :key="slot.index"
                    class="inv-slot" :class="slotClass(slot)" @click="toggleEdit(slot)">
                    <item-slot :item="slot" />
                  </div>
                </div>
              </div>
            </div>
            <div class="inv-row-pair">
              <div>
                <div class="inv-section-label">饰品（62–68）</div>
                <div class="inv-grid row-7">
                  <div v-for="slot in slotRange(62, 68)" :key="slot.index"
                    class="inv-slot" :class="slotClass(slot)" @click="toggleEdit(slot)">
                    <item-slot :item="slot" />
                  </div>
                </div>
              </div>
              <div>
                <div class="inv-section-label">时装饰品（72–78）</div>
                <div class="inv-grid row-7">
                  <div v-for="slot in slotRange(72, 78)" :key="slot.index"
                    class="inv-slot" :class="slotClass(slot)" @click="toggleEdit(slot)">
                    <item-slot :item="slot" />
                  </div>
                </div>
              </div>
            </div>
            <div class="inv-section-label">染料（79–88）</div>
            <div class="inv-grid row-10">
              <div v-for="slot in slotRange(79, 88)" :key="slot.index"
                class="inv-slot" :class="slotClass(slot)" @click="toggleEdit(slot)">
                <item-slot :item="slot" />
              </div>
            </div>
            <div class="inv-row-pair">
              <div>
                <div class="inv-section-label">其他装备（89–93）</div>
                <div class="inv-grid row-5">
                  <div v-for="slot in slotRange(89, 93)" :key="slot.index"
                    class="inv-slot" :class="slotClass(slot)" @click="toggleEdit(slot)">
                    <item-slot :item="slot" />
                  </div>
                </div>
              </div>
              <div>
                <div class="inv-section-label">其他装备染料（94–98）</div>
                <div class="inv-grid row-5">
                  <div v-for="slot in slotRange(94, 98)" :key="slot.index"
                    class="inv-slot" :class="slotClass(slot)" @click="toggleEdit(slot)">
                    <item-slot :item="slot" />
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- 存储 -->
          <template v-if="activeTab === 'storage'">
            <div v-for="store in storeSections" :key="store.label">
              <div class="inv-section-label">{{ store.label }}（{{ store.start }}–{{ store.end }}）</div>
              <div class="inv-grid row-10">
                <div v-for="slot in slotRange(store.start, store.end)" :key="slot.index"
                  class="inv-slot" :class="slotClass(slot)" @click="toggleEdit(slot)">
                  <item-slot :item="slot" />
                </div>
              </div>
            </div>
          </template>

          <!-- 三套装备栏（loadout） -->
          <template v-if="activeTab === 'loadout'">
            <div v-for="lo in loadoutSections" :key="lo.label">
              <div class="inv-loadout-card">
                <div class="inv-section-label">{{ lo.label }}</div>
                <div class="inv-section-label">装备（{{ lo.armorStart }}–{{ lo.armorEnd }}）</div>
                <div class="inv-grid row-10">
                  <div v-for="slot in slotRange(lo.armorStart, lo.armorEnd)" :key="slot.index"
                    class="inv-slot" :class="slotClass(slot)" @click="toggleEdit(slot)">
                    <item-slot :item="slot" />
                  </div>
                </div>
                <div class="inv-section-label">染料（{{ lo.dyeStart }}–{{ lo.dyeEnd }}）</div>
                <div class="inv-grid row-10">
                  <div v-for="slot in slotRange(lo.dyeStart, lo.dyeEnd)" :key="slot.index"
                    class="inv-slot" :class="slotClass(slot)" @click="toggleEdit(slot)">
                    <item-slot :item="slot" />
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- ── 详情 / 编辑面板 ─────────────────────────────── -->
          <transition name="edit-slide">
            <div v-if="selectedSlot" class="inv-edit-panel">
              <div class="inv-edit-header">
                <span v-if="canEdit">编辑 槽位 #{{ selectedSlot.index }}</span>
                <span v-else>物品详情 — 槽位 #{{ selectedSlot.index }}</span>
                <button class="inv-edit-close" @click="selectedSlot = null">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="13" height="13"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              </div>

              <!-- 只读详情 -->
              <div v-if="!canEdit" class="inv-detail-view">
                <div v-if="selectedSlot.net_id === 0" class="inv-detail-empty">空槽位</div>
                <template v-else>
                  <div class="inv-detail-icon-row">
                    <div class="inv-detail-icon">
                      <img :src="itemImage(selectedSlot.net_id)" class="detail-img"
                        @error="e => e.target.style.display='none'" />
                    </div>
                    <div class="inv-detail-meta">
                      <div class="inv-detail-name">{{ selectedSlot.name || '未知物品' }}</div>
                      <div v-if="selectedSlot.prefix_name" class="inv-detail-prefix">{{ selectedSlot.prefix_name }}</div>
                    </div>
                  </div>
                  <div class="inv-detail-rows">
                    <div class="inv-detail-row"><span class="drow-label">物品 ID</span><span class="drow-val">#{{ selectedSlot.net_id }}</span></div>
                    <div class="inv-detail-row"><span class="drow-label">数量</span><span class="drow-val">{{ selectedSlot.stack }}</span></div>
                    <div class="inv-detail-row"><span class="drow-label">前缀 ID</span><span class="drow-val">{{ selectedSlot.prefix || '无' }}</span></div>
                    <div class="inv-detail-row"><span class="drow-label">收藏</span><span class="drow-val">{{ selectedSlot.favorite ? '是' : '否' }}</span></div>
                    <div v-if="selectedSlot.prefix_name" class="inv-detail-row"><span class="drow-label">前缀名</span><span class="drow-val">{{ selectedSlot.prefix_name }}</span></div>
                  </div>
                </template>
              </div>

              <!-- 编辑表单 -->
              <template v-else>
                <div class="inv-edit-fields">
                  <div class="inv-field">
                    <label>物品 ID</label>
                    <input type="number" min="0" v-model.number="editNetId" class="inv-input" placeholder="0 = 空" />
                  </div>
                  <div class="inv-field">
                    <label>数量</label>
                    <input type="number" min="0" v-model.number="editStack" class="inv-input" />
                  </div>
                  <div class="inv-field">
                    <label>前缀 ID</label>
                    <input type="number" min="0" max="83" v-model.number="editPrefix" class="inv-input" placeholder="0 = 无" />
                  </div>
                  <div class="inv-field inv-field-inline">
                    <label class="inv-check-label">
                      <input type="checkbox" v-model="editFavorite" />
                      是否收藏
                    </label>
                  </div>
                  <div class="inv-edit-name" v-if="editNetId > 0">
                    当前名称：<strong>{{ selectedSlot.name || '(未知)' }}</strong>
                    <span class="inv-edit-prefix-name" v-if="editPrefix > 0">•前缀: {{ selectedSlot.prefix_name }}</span>
                  </div>
                </div>
                <div class="inv-edit-actions">
                  <button class="inv-btn inv-btn-danger-sm" @click="clearSlot">清空</button>
                  <button class="inv-btn inv-btn-primary-sm" @click="applyEdit">确认</button>
                </div>
              </template>
            </div>
          </transition>
        </div>

        <!-- ── 底部操作栏 ──────────────────────────────── -->
        <div class="inv-footer">
          <span v-if="canEdit" class="inv-footer-hint">点击格子可修改物品，修改后点击"保存"写入数据库</span>
          <span v-else class="inv-footer-hint">只读模式</span>
          <div class="inv-footer-btns">
            <button class="inv-btn inv-btn-outline" @click="$emit('close')">关闭</button>
            <button v-if="canEdit" class="inv-btn inv-btn-primary"
              :disabled="saving || !!error" @click="emitSave()">
              <span v-if="saving">保存中…</span>
              <span v-else>保存修改</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import ItemSlot from './ItemSlot.vue'
import { itemImage } from '@/utils/assetPath.js'

const props = defineProps({
  show:      { type: Boolean, default: false },
  username:  { type: String,  default: '' },
  loading:   { type: Boolean, default: false },
  error:     { type: String,  default: '' },
  slots:     { type: Array,   default: () => [] },
  health:    { type: Number,  default: 0 },
  maxHealth: { type: Number,  default: 0 },
  mana:      { type: Number,  default: 0 },
  maxMana:   { type: Number,  default: 0 },
  isOnline:  { type: Boolean, default: false },
  canEdit:   { type: Boolean, default: false },
  saving:    { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'save'])

// ── 本地 slots 副本（用于编辑）─────────────
const slotMap = ref({})  // { index: { index, net_id, prefix, stack, name, prefix_name } }

watch(() => props.slots, (s) => {
  const m = {}
  for (const slot of s) m[slot.index] = { ...slot }
  slotMap.value = m
}, { immediate: true })

// ── Tab ───────────────────────────────────
const activeTab = ref('main')
const TABS = [
  { id: 'main',    label: '主背包（0–57）' },
  { id: 'armor',   label: '防具/饰品/染料' },
  { id: 'storage', label: '存储（猪猪/保险箱等）' },
  { id: 'loadout', label: '三套装备（260–349）' },
]
const storeSections = [
  { label: '猪猪存钱罐', start: 99,  end: 138 },
  { label: '保险箱',     start: 139, end: 178 },
  { label: '护卫熔炉',   start: 180, end: 219 },
  { label: '虚空宝库',   start: 220, end: 259 },
]
const loadoutSections = [
  { label: '套装 1', armorStart: 260, armorEnd: 279, dyeStart: 280, dyeEnd: 289 },
  { label: '套装 2', armorStart: 290, armorEnd: 309, dyeStart: 310, dyeEnd: 319 },
  { label: '套装 3', armorStart: 320, armorEnd: 339, dyeStart: 340, dyeEnd: 349 },
]

// ── Slot helpers ──────────────────────────
function slotRange(from, to) {
  const result = []
  for (let i = from; i <= to; i++) {
    result.push(slotMap.value[i] ?? { index: i, net_id: 0, prefix: 0, stack: 0, favorite: 0, name: '', prefix_name: '' })
  }
  return result
}

function slotClass(slot) {
  return {
    'has-item':  slot.net_id !== 0,
    'is-selected': selectedSlot.value?.index === slot.index,
  }
}

// ── 编辑 ──────────────────────────────────
const selectedSlot = ref(null)
const editNetId  = ref(0)
const editStack  = ref(0)
const editPrefix = ref(0)
const editFavorite = ref(false)
const editMaxHealth = ref(0)
const editMaxMana = ref(0)
const editExtraSlot = ref(false)
const editUnlockedBiomeTorches = ref(false)
const editAteArtisanBread = ref(false)
const editUsedAegisCrystal = ref(false)
const editUsedAegisFruit = ref(false)
const editUsedArcaneCrystal = ref(false)
const editUsedGalaxyPearl = ref(false)
const editUsedGummyWorm = ref(false)
const editUsedAmbrosia = ref(false)
const editUnlockedSuperCart = ref(false)

watch(() => props.maxHealth, v => { editMaxHealth.value = v || 0 }, { immediate: true })
watch(() => props.maxMana, v => { editMaxMana.value = v || 0 }, { immediate: true })

function toggleEdit(slot) {
  if (selectedSlot.value?.index === slot.index) { selectedSlot.value = null; return }
  // 只读模式只展示详情，不填编辑字段
  if (!props.canEdit) { selectedSlot.value = { ...slot }; return }
  selectedSlot.value = { ...slot }
  editNetId.value  = slot.net_id
  editStack.value  = slot.stack > 0 ? slot.stack : 1
  editPrefix.value = slot.prefix
  editFavorite.value = !!slot.favorite
}

function applyEdit() {
  if (!selectedSlot.value) return
  const idx = selectedSlot.value.index
  const nextStack = (editNetId.value > 0)
    ? ((editStack.value || 0) > 0 ? editStack.value : 1)
    : 0
  slotMap.value[idx] = {
    ...slotMap.value[idx],
    net_id:  editNetId.value  || 0,
    stack:   nextStack,
    prefix:  editPrefix.value || 0,
    favorite: editFavorite.value ? 1 : 0,
    // 更新选中展示的 name（服务端之前提供的，本地不重新查）
    name:         editNetId.value !== selectedSlot.value.net_id ? '(需服务端验证)' : selectedSlot.value.name,
    prefix_name:  editPrefix.value !== selectedSlot.value.prefix ? '' : selectedSlot.value.prefix_name,
  }
  selectedSlot.value = null
}

function clearSlot() {
  if (!selectedSlot.value) return
  const idx = selectedSlot.value.index
  slotMap.value[idx] = { ...slotMap.value[idx], net_id: 0, stack: 0, prefix: 0, favorite: 0, name: '', prefix_name: '' }
  selectedSlot.value = null
}

function emitSave() {
  emit('save', {
    slots: slotMap.value,
    max_hp: editMaxHealth.value,
    max_mana: editMaxMana.value,
    extraSlot: editExtraSlot.value ? 1 : 0,
    unlockedBiomeTorches: editUnlockedBiomeTorches.value ? 1 : 0,
    ateArtisanBread: editAteArtisanBread.value ? 1 : 0,
    usedAegisCrystal: editUsedAegisCrystal.value ? 1 : 0,
    usedAegisFruit: editUsedAegisFruit.value ? 1 : 0,
    usedArcaneCrystal: editUsedArcaneCrystal.value ? 1 : 0,
    usedGalaxyPearl: editUsedGalaxyPearl.value ? 1 : 0,
    usedGummyWorm: editUsedGummyWorm.value ? 1 : 0,
    usedAmbrosia: editUsedAmbrosia.value ? 1 : 0,
    unlockedSuperCart: editUnlockedSuperCart.value ? 1 : 0,
  })
}
</script>


<style scoped>
/* ── overlay / panel ───────────────────────── */
.inv-overlay {
  position: fixed; inset: 0; z-index: 1010;
  background: rgba(0,0,0,.6);
  display: flex; align-items: center; justify-content: center;
  padding: 16px;
}
.inv-panel {
  background: #fff; border-radius: 14px;
  width: min(860px, 100%); max-height: 90vh;
  display: flex; flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,.25);
  overflow: hidden;
}
.inv-fade-enter-active, .inv-fade-leave-active { transition: opacity .2s; }
.inv-fade-enter-from, .inv-fade-leave-to { opacity: 0; }
.inv-fade-enter-active .inv-panel,
.inv-fade-leave-active .inv-panel { transition: transform .2s; }
.inv-fade-enter-from .inv-panel { transform: translateY(20px); }

/* ── header ────────────────────────────────── */
.inv-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 20px; background: #f8fafc; border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}
.inv-header-left { display: flex; align-items: center; gap: 10px; }
.inv-icon { width: 18px; height: 18px; stroke: #6c63ff; }
.inv-title { font-size: 1rem; font-weight: 700; color: #0f172a; }
.online-badge  { background: #dcfce7; color: #15803d; font-size: .72rem; font-weight: 600; padding: 2px 8px; border-radius: 20px; }
.offline-badge { background: #f1f5f9; color: #64748b; font-size: .72rem; font-weight: 600; padding: 2px 8px; border-radius: 20px; }
.inv-header-right { display: flex; align-items: center; gap: 12px; }
.inv-stat { font-size: .82rem; color: #64748b; }
.inv-close-btn {
  background: none; border: none; cursor: pointer; padding: 4px;
  border-radius: 6px; color: #64748b; display: flex; align-items: center;
}
.inv-close-btn:hover { background: #f1f5f9; color: #0f172a; }

/* ── warning bar ────────────────────────────── */
.inv-warn {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 20px; background: #fefce8;
  border-bottom: 1px solid #fef08a;
  font-size: .82rem; color: #854d0e; flex-shrink: 0;
}

.inv-stat-edit {
  margin: 10px 16px 0;
  padding: 10px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}
.inv-stat-edit-title {
  font-size: .78rem;
  font-weight: 700;
  color: #475569;
  margin-bottom: 8px;
}
.inv-stat-edit-row {
  display: grid;
  grid-template-columns: auto 120px auto 120px;
  gap: 8px;
  align-items: center;
}
.inv-stat-edit-row label {
  font-size: .76rem;
  color: #64748b;
}

.inv-buff-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.inv-buff-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: .76rem;
  color: #475569;
  cursor: pointer;
  padding: 6px 10px;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  transition: all 0.2s;
  user-select: none;
}
.inv-buff-toggle:hover {
  border-color: #94a3b8;
  background: #f1f5f9;
}
.inv-buff-toggle input[type="checkbox"] {
  accent-color: #3b82f6;
  width: 14px;
  height: 14px;
  cursor: pointer;
  margin: 0;
}

/* ── tabs ───────────────────────────────────── */
.inv-tabs {
  display: flex; gap: 2px; padding: 10px 16px 0;
  border-bottom: 1px solid #e2e8f0; flex-shrink: 0;
}
.inv-tab {
  padding: 6px 16px; border-radius: 6px 6px 0 0;
  background: none; border: 1px solid transparent; border-bottom: none;
  font-size: .82rem; color: #64748b; cursor: pointer; transition: all .15s;
  margin-bottom: -1px;
}
.inv-tab:hover { background: #f1f5f9; }
.inv-tab.active {
  background: #fff; border-color: #e2e8f0; color: #0f172a;
  font-weight: 600; border-bottom-color: #fff;
}

/* ── body ───────────────────────────────────── */
.inv-body { flex: 1; overflow-y: auto; padding: 16px 20px; }
.inv-loading { text-align: center; padding: 40px; color: #94a3b8; }
.inv-error {
  display: flex; align-items: center; gap: 8px;
  padding: 20px; color: #e44c65; background: #fef2f2;
  border-radius: 8px; font-size: .88rem;
}

/* ── section labels & grid ──────────────────── */
.inv-section-label {
  font-size: .72rem; font-weight: 700; color: #94a3b8;
  letter-spacing: .06em; text-transform: uppercase;
  margin: 12px 0 6px;
}
.inv-grid { display: flex; flex-wrap: wrap; gap: 4px; }
.inv-row-pair { display: flex; gap: 24px; align-items: flex-start; }
.inv-loadout-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 10px;
  background: #fafcff;
}

/* ── slot ───────────────────────────────────── */
.inv-slot {
  width: 52px; height: 52px;
  background: #f1f5f9; border: 1.5px solid #e2e8f0;
  border-radius: 6px; cursor: pointer;
  transition: border-color .12s, background .12s;
  position: relative; overflow: hidden;
  display: flex; align-items: center; justify-content: center;
}
.inv-slot:hover { border-color: #6c63ff; background: #f5f3ff; }
.inv-slot.has-item { background: #eff6ff; border-color: #bfdbfe; }
.inv-slot.has-item:hover { border-color: #6c63ff; background: #ede9fe; }
.inv-slot.is-selected { border-color: #6c63ff !important; background: #ede9fe !important; box-shadow: 0 0 0 2px rgba(108,99,255,.3); }
.slot-inner { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; height: 100%; padding: 2px; position: relative; }
.slot-img {
  width: 36px; height: 36px;
  object-fit: contain;
  image-rendering: pixelated;
}
.slot-stack {
  position: absolute; bottom: 1px; right: 2px;
  font-size: .6rem; font-weight: 700; color: #0f172a;
  background: rgba(255,255,255,.8); border-radius: 3px; padding: 0 2px;
}
.slot-empty { font-size: .7rem; color: #cbd5e1; }

/* ── edit panel ─────────────────────────────── */
.inv-edit-panel {
  margin-top: 14px; padding: 14px 16px;
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;
}
.inv-edit-header {
  display: flex; align-items: center; justify-content: space-between;
  font-size: .84rem; font-weight: 600; color: #0f172a; margin-bottom: 10px;
}
.inv-edit-close {
  background: none; border: none; cursor: pointer; color: #94a3b8; padding: 2px; border-radius: 4px;
}
.inv-edit-close:hover { background: #e2e8f0; }
.inv-edit-fields { display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-end; }
.inv-field { display: flex; flex-direction: column; gap: 4px; }
.inv-field label { font-size: .76rem; color: #64748b; font-weight: 500; }
.inv-input {
  background: #fff; border: 1px solid #d1d5db; border-radius: 6px;
  padding: 5px 10px; font-size: .82rem; color: #0f172a; width: 90px;
}
.inv-input:focus { outline: none; border-color: #6c63ff; }
.inv-edit-name { font-size: .78rem; color: #475569; margin-top: 6px; align-self: flex-end; }
.inv-edit-prefix-name { color: #6c63ff; margin-left: 6px; }
.inv-edit-actions { display: flex; gap: 8px; margin-top: 10px; }
.edit-slide-enter-active, .edit-slide-leave-active { transition: all .2s; }
.edit-slide-enter-from, .edit-slide-leave-to { opacity: 0; transform: translateY(-6px); }

/* ── footer ─────────────────────────────────── */
.inv-footer {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 20px; background: #f8fafc; border-top: 1px solid #e2e8f0;
  flex-shrink: 0; gap: 12px;
}
.inv-footer-hint { font-size: .78rem; color: #94a3b8; }
.inv-footer-btns { display: flex; gap: 8px; }

/* ── 通用按钮 ────────────────────────────────── */
.inv-btn {
  display: inline-flex; align-items: center; gap: 5px;
  border: none; border-radius: 7px; cursor: pointer;
  font-size: .82rem; font-weight: 500; padding: 7px 16px;
  transition: opacity .15s;
}
.inv-btn:disabled { opacity: .45; cursor: not-allowed; }
.inv-btn-primary      { background: #6c63ff; color: #fff; }
.inv-btn-primary:hover:not(:disabled) { background: #5b52e0; }
.inv-btn-outline      { background: transparent; border: 1px solid #d1d5db; color: #374151; }
.inv-btn-outline:hover:not(:disabled) { background: #f1f5f9; }
.inv-btn-primary-sm   { background: #6c63ff; color: #fff; padding: 4px 12px; font-size: .76rem; }
.inv-btn-danger-sm    { background: rgba(228,76,101,.15); color: #e44c65; border: 1px solid rgba(228,76,101,.3); padding: 4px 12px; font-size: .76rem; }

/* ── 只读详情视图 ─────────────────────────────── */
.inv-detail-view { padding: 4px 0; }
.inv-detail-empty { font-size: .82rem; color: #94a3b8; }
.inv-detail-icon-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.inv-detail-icon {
  width: 52px; height: 52px; background: #f1f5f9; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.detail-img { width: 40px; height: 40px; object-fit: contain; image-rendering: pixelated; }
.inv-detail-meta { display: flex; flex-direction: column; gap: 3px; }
.inv-detail-name   { font-size: .92rem; font-weight: 700; color: #0f172a; }
.inv-detail-prefix { font-size: .78rem; color: #6c63ff; font-weight: 600; }
.inv-detail-rows   { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
.inv-detail-row    { display: flex; flex-direction: column; gap: 1px; }
.drow-label { font-size: .68rem; color: #94a3b8; }
.drow-val   { font-size: .82rem; color: #0f172a; font-weight: 500; }

@media (max-width: 768px) {
  .inv-panel {
    width: 100vw;
    max-width: 100vw;
    border-radius: 16px 16px 0 0;
    max-height: 90vh;
    padding: 14px;
  }
  .inv-grid { grid-template-columns: repeat(auto-fill, minmax(48px, 1fr)); gap: 4px; }
  .inv-tabs { overflow-x: auto; flex-wrap: nowrap; gap: 4px; }
  .inv-tab { flex-shrink: 0; font-size: 12px; padding: 5px 10px; }
  .inv-header { flex-wrap: wrap; gap: 8px; }
  .inv-stat-edit-row { flex-wrap: wrap; gap: 6px; }
  .inv-buff-grid { grid-template-columns: 1fr 1fr; }
  .inv-detail-rows { grid-template-columns: 1fr; }
}
</style>
