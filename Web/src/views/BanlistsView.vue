<template>
  <div class="bl-page">
    <PageHeader title="物品/弹幕/图格封禁管理" subtitle="TShock 物品·弹幕·图格黑名单" heading-tag="h1">
      <template #actions>
        <button class="btn btn-sm btn-outline" @click="loadData" :disabled="loading || !agentOnline || !activeServerKey">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
          </svg>
          {{ loading ? '加载中…' : '刷新' }}
        </button>
        <button class="btn btn-sm btn-outline" @click="doReload" :disabled="!agentOnline || !activeServerKey || reloading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 1 1-.49-3.18"/>
          </svg>
          {{ reloading ? '重载中…' : '立即重载' }}
        </button>
        <button class="btn btn-sm btn-primary" @click="doSave" :disabled="!agentOnline || !activeServerKey || saving">
          <svg v-if="saving" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0;animation:spin .8s linear infinite">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </template>
    </PageHeader>

    <AgentOfflineNotice v-if="!agentOnline" message="Agent 未连接，无法管理封禁列表。请先启动服务器。" />

    <div v-else class="bl-body">
      <div v-if="!activeServerKey" class="state-box state-empty">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <line x1="9" y1="3" x2="9" y2="21"/>
          <line x1="15" y1="3" x2="15" y2="21"/>
          <line x1="3" y1="9" x2="21" y2="9"/>
          <line x1="3" y1="15" x2="21" y2="15"/>
        </svg>
        <p>请先在左侧选择一个服务器</p>
      </div>

      <div v-else-if="loading" class="state-box state-loading">
        <div class="spinner"></div>
        <span>正在加载封禁数据…</span>
      </div>

      <div v-else-if="loadError" class="state-box state-error">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <div>
          <strong>加载失败</strong>
          <p>{{ loadError }}</p>
          <button class="btn btn-sm btn-outline" style="margin-top:8px" @click="loadData">重试</button>
        </div>
      </div>

      <template v-else>
        <div v-if="toast" :class="['toast', toast.ok ? 'toast-ok' : 'toast-err']">
          {{ toast.msg }}
          <button class="toast-close" @click="toast = null">✕</button>
        </div>

        <div class="body-toolbar">
          <button class="btn btn-sm btn-primary" @click="openCreate" :disabled="!agentOnline || !activeServerKey">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:13px;height:13px;flex-shrink:0">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            新增封禁
          </button>
        </div>

        <div class="tabs">
          <button :class="['tab', { active: activeTab === 'item' }]" @click="activeTab = 'item'">
            物品封禁 <span class="tab-count">{{ itemItems.length }}</span>
          </button>
          <button :class="['tab', { active: activeTab === 'proj' }]" @click="activeTab = 'proj'">
            弹幕封禁 <span class="tab-count">{{ projItems.length }}</span>
          </button>
          <button :class="['tab', { active: activeTab === 'tile' }]" @click="activeTab = 'tile'">
            图格封禁 <span class="tab-count">{{ tileItems.length }}</span>
          </button>
        </div>

        <div class="search-bar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input v-model="searchQuery" class="search-input" :placeholder="'搜索 ' + tabLabel + ' ID 或名称…'" />
          <button v-if="searchQuery" class="search-clear" @click="searchQuery = ''">✕</button>
        </div>

        <div class="bl-table-wrap">
          <table class="bl-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>名称</th>
                <th>允许的组</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!pagedItems.length">
                <td colspan="4" class="empty-row">
                  {{ searchQuery ? '没有符合搜索条件的记录' : '暂无 ' + tabLabel + ' 封禁记录' }}
                </td>
              </tr>
              <tr v-for="item in pagedItems" :key="item.key">
                <td>
                  <span v-if="item.id > 0" class="item-id">{{ item.id }}</span>
                  <span v-else class="item-id item-id-empty">无ID</span>
                </td>
                <td>
                  <div class="name-cell">
                    <img
                      v-if="activeTab === 'item' && item.id > 0"
                      :src="itemImage(item.id)"
                      class="item-icon"
                      @error="hideBrokenImage"
                    />
                    <span>{{ item.displayName }}</span>
                  </div>
                </td>
                <td>
                  <div v-if="item.allowedGroups.length" class="groups-cell">
                    <span v-for="g in item.allowedGroups" :key="g" class="group-badge">{{ g }}</span>
                  </div>
                  <span v-else class="group-badge-empty">未设置</span>
                </td>
                <td>
                  <div class="row-actions">
                    <button
                      class="btn btn-xs btn-outline"
                      @click="openEditGroups(item)"
                      :disabled="submitting || item.id <= 0"
                      :title="item.id <= 0 ? '该记录无法解析出ID，暂不可编辑' : ''"
                    >
                      编辑组
                    </button>
                    <button
                      class="btn btn-xs btn-danger"
                      @click="confirmRemove(item)"
                      :disabled="submitting || item.id <= 0"
                      :title="item.id <= 0 ? '该记录无法解析出ID，暂不可移除' : ''"
                    >
                      移除
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="filteredItems.length > pageSize" class="pagination">
          <button class="btn btn-xs btn-outline" :disabled="page <= 1" @click="page--">上一页</button>
          <span class="page-info">第 {{ page }} 页 / 共 {{ totalPages }} 页（{{ filteredItems.length }} 条）</span>
          <button class="btn btn-xs btn-outline" :disabled="page >= totalPages" @click="page++">下一页</button>
        </div>
      </template>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-box modal-box-wide">
        <div class="modal-header">
          <h3>新增 {{ tabLabelByType(form.type) }}封禁</h3>
          <button class="modal-close" @click="closeModal">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-field">
            <label class="form-label">类型</label>
            <div class="type-selector">
              <button :class="['type-btn', { active: form.type === 'item' }]" @click="setFormType('item')">物品</button>
              <button :class="['type-btn', { active: form.type === 'proj' }]" @click="setFormType('proj')">弹幕</button>
              <button :class="['type-btn', { active: form.type === 'tile' }]" @click="setFormType('tile')">图格</button>
            </div>
          </div>

          <div class="form-field">
            <label class="form-label">搜索并选择 ID <span class="required">*</span></label>
            <div class="id-search-wrap">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              <input
                v-model="idSearchQuery"
                class="id-search-input"
                :placeholder="'输入 ID 或 ' + tabLabelByType(form.type) + ' 名称搜索…'"
                @input="idSearchPage = 1"
              />
              <button v-if="idSearchQuery" class="search-clear" @click="idSearchQuery = ''">✕</button>
            </div>

            <div class="id-result-list">
              <div v-if="idsLoading" class="id-result-empty">加载 ID 数据中…</div>
              <div v-else-if="!filteredIdList.length" class="id-result-empty">无匹配结果</div>
              <template v-else>
                <div
                  v-for="entry in pagedIdList"
                  :key="entry.id"
                  :class="['id-result-item', { selected: Number(form.id) === Number(entry.id) }]"
                  @click="form.id = Number(entry.id)"
                >
                  <img
                    v-if="form.type === 'item'"
                    :src="itemImage(entry.id)"
                    class="id-item-img"
                    @error="hideBrokenImage"
                  />
                  <span class="id-num">#{{ entry.id }}</span>
                  <span class="id-zhname">{{ entry.zhName || '—' }}</span>
                  <span class="id-enname">{{ entry.enName || '' }}</span>
                </div>

                <div v-if="filteredIdList.length > idPageSize" class="id-result-pagination">
                  <button class="btn btn-xs btn-outline" :disabled="idSearchPage <= 1" @click="idSearchPage--">上一页</button>
                  <span>{{ idSearchPage }} / {{ idTotalPages }}（{{ filteredIdList.length }} 项）</span>
                  <button class="btn btn-xs btn-outline" :disabled="idSearchPage >= idTotalPages" @click="idSearchPage++">下一页</button>
                </div>
              </template>
            </div>

            <div v-if="form.id" class="selected-hint">
              <img
                v-if="form.type === 'item'"
                :src="itemImage(form.id)"
                class="hint-item-img"
                @error="hideBrokenImage"
              />
              <span class="hint-id-badge">#{{ form.id }}</span>
              <span class="hint-name">{{ currentSelectedName || '（无中文名）' }}</span>
              <button class="hint-clear" @click="clearSelection">✕ 取消选择</button>
            </div>
          </div>

          <div class="form-field">
            <label class="form-label">允许的组 <span class="required">*</span></label>
            <div class="group-multiselect-wrap">
              <input
                v-model="groupSearch"
                class="form-input"
                placeholder="搜索组名…"
                @focus="groupDropdownOpen = true"
                @input="groupDropdownOpen = true"
                @blur="onGroupBlur"
              />
              <div v-if="groupDropdownOpen" class="group-dropdown">
                <div v-if="groupsLoading" class="group-dropdown-empty">加载组列表中…</div>
                <div v-else-if="!filteredGroups.length" class="group-dropdown-empty">无匹配组</div>
                <template v-else>
                  <div
                    v-for="g in filteredGroups"
                    :key="g"
                    :class="['group-dropdown-item', { selected: form.allowedGroups.includes(g) }]"
                    @mousedown.prevent="toggleGroup(g)"
                  >
                    <span>{{ g }}</span>
                  </div>
                </template>
              </div>
              <div class="group-selected-list">
                <span v-for="g in form.allowedGroups" :key="g" class="group-selected-item">
                  {{ g }}
                  <button class="group-remove-btn" @click="removeGroup(g)">×</button>
                </span>
                <span v-if="!form.allowedGroups.length" class="group-selected-empty">未选择</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn btn-outline" @click="closeModal">取消</button>
          <button class="btn btn-danger" @click="submitAdd" :disabled="submitDisabled">
            {{ submitting ? '添加中…' : '确认添加' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="removeTarget" class="modal-overlay" @click.self="removeTarget = null">
      <div class="modal-box modal-box-sm">
        <div class="modal-header">
          <h3>确认移除封禁</h3>
          <button class="modal-close" @click="removeTarget = null">✕</button>
        </div>
        <div class="modal-body">
          <p>
            确定要移除 ID 为
            <strong>{{ removeTarget.id }}</strong>
            （{{ removeTarget.displayName || '未知名称' }}）
            的 {{ tabLabel }} 封禁吗？
          </p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="removeTarget = null">取消</button>
          <button class="btn btn-primary" @click="doRemove" :disabled="submitting">
            {{ submitting ? '处理中…' : '确认移除' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="editTarget" class="modal-overlay" @click.self="closeEditGroups">
      <div class="modal-box modal-box-sm">
        <div class="modal-header">
          <h3>编辑允许组</h3>
          <button class="modal-close" @click="closeEditGroups">✕</button>
        </div>
        <div class="modal-body">
          <p class="edit-meta">{{ tabLabelByType(editTarget.type) }} #{{ editTarget.id }} · {{ editTarget.displayName }}</p>
          <div class="form-field">
            <label class="form-label">允许的组 <span class="required">*</span></label>
            <div class="group-multiselect-wrap">
              <input
                v-model="editGroupSearch"
                class="form-input"
                placeholder="搜索组名…"
                @focus="editGroupDropdownOpen = true"
                @input="editGroupDropdownOpen = true"
                @blur="onEditGroupBlur"
              />
              <div v-if="editGroupDropdownOpen" class="group-dropdown">
                <div v-if="groupsLoading" class="group-dropdown-empty">加载组列表中…</div>
                <div v-else-if="!filteredEditGroups.length" class="group-dropdown-empty">无匹配组</div>
                <template v-else>
                  <div
                    v-for="g in filteredEditGroups"
                    :key="g"
                    :class="['group-dropdown-item', { selected: editAllowedGroups.includes(g) }]"
                    @mousedown.prevent="toggleEditGroup(g)"
                  >
                    <span>{{ g }}</span>
                  </div>
                </template>
              </div>
              <div class="group-selected-list">
                <span v-for="g in editAllowedGroups" :key="g" class="group-selected-item">
                  {{ g }}
                  <button class="group-remove-btn" @click="removeEditGroup(g)">×</button>
                </span>
                <span v-if="!editAllowedGroups.length" class="group-selected-empty">未选择</span>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="closeEditGroups">取消</button>
          <button class="btn btn-primary" @click="submitUpdateGroups" :disabled="submitting || !editAllowedGroups.length">
            {{ submitting ? '保存中…' : '保存修改' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, onMounted, onUnmounted, ref, watch } from 'vue'
import { getListByType, getZhName, loadTerrariaIDs } from '@/config/terraria_ids'
import AgentOfflineNotice from '@/components/AgentOfflineNotice.vue'
import PageHeader from '@/components/PageHeader.vue'
import { itemImage } from '@/utils/assetPath.js'

const props = defineProps({
  agentOnline: { type: Boolean, default: false },
})

const activeServerKey = inject('activeServerKey', ref(''))

const loading = ref(false)
const loadError = ref('')
const tileItems = ref([])
const itemItems = ref([])
const projItems = ref([])
const toast = ref(null)
const showModal = ref(false)
const removeTarget = ref(null)
const submitting = ref(false)
const reloading = ref(false)
const saving = ref(false)
const activeTab = ref('item')
const searchQuery = ref('')
const page = ref(1)
const pageSize = 30

const terrariaMaps = ref(null)
const idsLoading = ref(false)
const idSearchQuery = ref('')
const idSearchPage = ref(1)
const idPageSize = 50

const groups = ref([])
const groupsLoading = ref(false)
const groupSearch = ref('')
const groupDropdownOpen = ref(false)
const editTarget = ref(null)
const editAllowedGroups = ref([])
const editGroupSearch = ref('')
const editGroupDropdownOpen = ref(false)
const banGroupFallbackMap = ref(new Map())

const form = ref({ type: 'item', id: '', allowedGroups: [] })

const tabLabelByType = (t) => ({ tile: '图格', item: '物品', proj: '弹幕' }[t] || '')
const tabLabel = computed(() => tabLabelByType(activeTab.value))

function hideBrokenImage(event) {
  const img = event?.target
  if (!img) return

  const currentSrc = String(img.getAttribute('src') || '')
  if (!img.dataset.fallbackTried) {
    const itemsPath = import.meta.env.BASE_URL + 'items/'
    const resourcesItemsPath = import.meta.env.BASE_URL + 'resources/items/'
    if (currentSrc.includes(itemsPath)) {
      img.dataset.fallbackTried = '1'
      img.src = currentSrc.replace(itemsPath, resourcesItemsPath)
      return
    }
    if (currentSrc.includes(resourcesItemsPath)) {
      img.dataset.fallbackTried = '1'
      img.src = currentSrc.replace(resourcesItemsPath, itemsPath)
      return
    }
  }

  img.style.display = 'none'
}

function parseAllowedGroups(raw) {
  if (Array.isArray(raw)) {
    return raw.map((x) => String(x || '').trim()).filter(Boolean)
  }
  if (typeof raw === 'string') {
    return raw.split(/[;,\n\r\t ]+/).map((x) => x.trim()).filter(Boolean)
  }
  return []
}

function resolveItemIdFromName(name) {
  if (!name || !terrariaMaps.value) return 0
  const target = String(name).trim().toLowerCase()
  const found = terrariaMaps.value.itemList.find((x) => {
    return String(x.enName || '').trim().toLowerCase() === target || String(x.zhName || '').trim().toLowerCase() === target
  })
  return found ? Number(found.id) : 0
}

function normalizeRow(type, row) {
  const id = Number(row?.id || 0) || (type === 'item' ? resolveItemIdFromName(row?.name) : 0)
  const zhName = id > 0 ? getZhName(type, id, terrariaMaps.value) : ''
  const displayName = zhName || row?.name || (id > 0 ? `ID ${id}` : '—')
  const key = `${type}:${id}`
  const fromServer = parseAllowedGroups(row?.allowedGroups ?? row?.allowed_groups)
  const allowedGroups = fromServer.length ? fromServer : (banGroupFallbackMap.value.get(key) || [])
  return {
    key: `${type}-${id || row?.name || Math.random()}`,
    id,
    displayName,
    allowedGroups,
  }
}

const currentItems = computed(() => {
  if (activeTab.value === 'tile') return tileItems.value
  if (activeTab.value === 'item') return itemItems.value
  return projItems.value
})

const filteredItems = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return currentItems.value
  return currentItems.value.filter((i) => {
    return String(i.id).includes(q) || String(i.displayName || '').toLowerCase().includes(q) || i.allowedGroups.some((g) => String(g).toLowerCase().includes(q))
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredItems.value.length / pageSize)))
const pagedItems = computed(() => {
  const start = (page.value - 1) * pageSize
  return filteredItems.value.slice(start, start + pageSize)
})

const filteredIdList = computed(() => {
  if (!terrariaMaps.value) return []
  const list = getListByType(form.value.type, terrariaMaps.value)
  const q = idSearchQuery.value.trim().toLowerCase()
  if (!q) return list
  return list.filter((e) => {
    return String(e.id).includes(q) || String(e.zhName || '').toLowerCase().includes(q) || String(e.enName || '').toLowerCase().includes(q)
  })
})

const idTotalPages = computed(() => Math.max(1, Math.ceil(filteredIdList.value.length / idPageSize)))
const pagedIdList = computed(() => {
  const start = (idSearchPage.value - 1) * idPageSize
  return filteredIdList.value.slice(start, start + idPageSize)
})

const filteredGroups = computed(() => {
  const q = groupSearch.value.trim().toLowerCase()
  if (!q) return groups.value
  return groups.value.filter((g) => String(g || '').toLowerCase().includes(q))
})

const filteredEditGroups = computed(() => {
  const q = editGroupSearch.value.trim().toLowerCase()
  if (!q) return groups.value
  return groups.value.filter((g) => String(g || '').toLowerCase().includes(q))
})

const currentSelectedName = computed(() => {
  if (!form.value.id || !terrariaMaps.value) return ''
  return getZhName(form.value.type, Number(form.value.id), terrariaMaps.value)
})

const submitDisabled = computed(() => {
  return submitting.value || !form.value.id || !form.value.allowedGroups.length
})

async function loadTerrariaData() {
  idsLoading.value = true
  terrariaMaps.value = await loadTerrariaIDs()
  idsLoading.value = false
}

function loadData() {
  if (!activeServerKey.value) return
  loading.value = true
  loadError.value = ''
  window.__tshockSend?.({
    type: 'list_banlists',
    msg_id: `bl-list-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

function fetchGroups() {
  if (!activeServerKey.value) return
  groupsLoading.value = true
  window.__tshockSend?.({
    type: 'get_groups',
    msg_id: `bl-groups-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

function openCreate() {
  form.value = { type: activeTab.value, id: '', allowedGroups: [] }
  idSearchQuery.value = ''
  idSearchPage.value = 1
  groupSearch.value = ''
  groupDropdownOpen.value = false
  showModal.value = true
  if (!groups.value.length) fetchGroups()
}

function closeModal() {
  showModal.value = false
}

function setFormType(type) {
  form.value.type = type
  form.value.id = ''
  idSearchQuery.value = ''
  idSearchPage.value = 1
}

function clearSelection() {
  form.value.id = ''
  idSearchQuery.value = ''
}

function toggleGroup(groupName) {
  const normalized = String(groupName || '').trim()
  if (!normalized) return

  if (form.value.allowedGroups.includes(normalized)) {
    form.value.allowedGroups = form.value.allowedGroups.filter((x) => x !== normalized)
  } else {
    form.value.allowedGroups = [...form.value.allowedGroups, normalized]
  }
}

function removeGroup(groupName) {
  form.value.allowedGroups = form.value.allowedGroups.filter((x) => x !== groupName)
}

function onGroupBlur() {
  setTimeout(() => {
    groupDropdownOpen.value = false
  }, 160)
}

function onEditGroupBlur() {
  setTimeout(() => {
    editGroupDropdownOpen.value = false
  }, 160)
}

function openEditGroups(item) {
  editTarget.value = {
    type: activeTab.value,
    id: Number(item.id),
    displayName: item.displayName || `ID ${item.id}`,
  }
  editAllowedGroups.value = [...(item.allowedGroups || [])]
  editGroupSearch.value = ''
  editGroupDropdownOpen.value = false
  if (!groups.value.length) fetchGroups()
}

function closeEditGroups() {
  editTarget.value = null
  editAllowedGroups.value = []
  editGroupSearch.value = ''
  editGroupDropdownOpen.value = false
}

function toggleEditGroup(groupName) {
  const normalized = String(groupName || '').trim()
  if (!normalized) return
  if (editAllowedGroups.value.includes(normalized)) {
    editAllowedGroups.value = editAllowedGroups.value.filter((x) => x !== normalized)
  } else {
    editAllowedGroups.value = [...editAllowedGroups.value, normalized]
  }
}

function removeEditGroup(groupName) {
  editAllowedGroups.value = editAllowedGroups.value.filter((x) => x !== groupName)
}

function submitUpdateGroups() {
  if (!activeServerKey.value || !editTarget.value?.id) return
  submitting.value = true
  const normalizedGroups = editAllowedGroups.value.map((x) => String(x || '').trim()).filter(Boolean)
  const groupsCsv = normalizedGroups.join(',')
  const key = `${editTarget.value.type}:${Number(editTarget.value.id)}`
  banGroupFallbackMap.value.set(key, normalizedGroups)

  window.__tshockSend?.({
    type: 'update_banlist_groups',
    msg_id: `bl-update-${Date.now()}`,
    timestamp: Date.now(),
    payload: {
      agent_key: activeServerKey.value,
      ban_type: editTarget.value.type,
      id: Number(editTarget.value.id),
      allowedGroups: groupsCsv,
      allowed_groups: groupsCsv,
      allowedGroupsList: normalizedGroups,
      allowed_groups_list: normalizedGroups,
      groups: normalizedGroups,
    },
  })
}

function submitAdd() {
  if (!activeServerKey.value || !form.value.id) return
  submitting.value = true
  const normalizedGroups = form.value.allowedGroups.map((x) => String(x || '').trim()).filter(Boolean)
  const groupsCsv = normalizedGroups.join(',')

  // 当服务端响应缺少分组信息时，回退使用前端已选择的分组。
  banGroupFallbackMap.value.set(`${form.value.type}:${Number(form.value.id)}`, normalizedGroups)

  window.__tshockSend?.({
    type: 'add_banlist',
    msg_id: `bl-add-${Date.now()}`,
    timestamp: Date.now(),
    payload: {
      agent_key: activeServerKey.value,
      ban_type: form.value.type,
      id: Number(form.value.id),
      allowedGroups: groupsCsv,
      allowed_groups: groupsCsv,
      allowedGroupsList: normalizedGroups,
      allowed_groups_list: normalizedGroups,
      groups: normalizedGroups,
    },
  })
}

function confirmRemove(item) {
  removeTarget.value = item
}

function doRemove() {
  if (!removeTarget.value || !activeServerKey.value || removeTarget.value.id <= 0) return
  submitting.value = true
  banGroupFallbackMap.value.delete(`${activeTab.value}:${Number(removeTarget.value.id)}`)
  window.__tshockSend?.({
    type: 'remove_banlist',
    msg_id: `bl-del-${Date.now()}`,
    timestamp: Date.now(),
    payload: {
      agent_key: activeServerKey.value,
      ban_type: activeTab.value,
      id: Number(removeTarget.value.id),
    },
  })
}

function showToast(ok, msg) {
  toast.value = { ok, msg }
  setTimeout(() => {
    toast.value = null
  }, 3200)
}

function doReload() {
  if (!activeServerKey.value) return
  reloading.value = true
  window.__tshockSend?.({
    type: 'reload_tshock',
    msg_id: `bl-reload-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

function doSave() {
  if (!activeServerKey.value) return
  saving.value = true
  window.__tshockSend?.({
    type: 'save_world',
    msg_id: `bl-save-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

function onWsMessage(event) {
  const pkt = event.detail || {}
  const p = pkt.payload || {}

  if (pkt.type === 'list_banlists_resp') {
    loading.value = false
    if (p.success) {
      tileItems.value = (p.tiles || []).map((x) => normalizeRow('tile', x))
      itemItems.value = (p.items || []).map((x) => normalizeRow('item', x))
      projItems.value = (p.projectiles || []).map((x) => normalizeRow('proj', x))
      page.value = 1
    } else {
      loadError.value = p.msg || '加载失败'
    }
    return
  }

  if (pkt.type === 'add_banlist_resp') {
    submitting.value = false
    showToast(!!p.success, p.msg || (p.success ? '添加成功' : '添加失败'))
    if (p.success) {
      closeModal()
      loadData()
    }
    return
  }

  if (pkt.type === 'remove_banlist_resp') {
    submitting.value = false
    showToast(!!p.success, p.msg || (p.success ? '已移除' : '移除失败'))
    if (p.success) {
      removeTarget.value = null
      loadData()
    }
    return
  }

  if (pkt.type === 'update_banlist_groups_resp') {
    submitting.value = false
    showToast(!!p.success, p.msg || (p.success ? '修改成功' : '修改失败'))
    if (p.success) {
      closeEditGroups()
      loadData()
    }
    return
  }

  if (pkt.type === 'reload_tshock_resp') {
    reloading.value = false
    showToast(!!p.success, p.msg || (p.success ? '重载成功' : '重载失败'))
    return
  }

  if (pkt.type === 'save_world_resp') {
    saving.value = false
    showToast(!!p.success, p.msg || (p.success ? '保存成功' : '保存失败'))
    return
  }

  if (pkt.type === 'get_groups_resp') {
    groupsLoading.value = false
    if (p.success && Array.isArray(p.groups)) {
      groups.value = p.groups
        .map((x) => (typeof x === 'string' ? x : (x?.name || x?.Name || '')))
        .map((x) => String(x || '').trim())
        .filter(Boolean)
    } else {
      groups.value = []
    }
  }
}

onMounted(async () => {
  window.addEventListener('ws-message', onWsMessage)
  await loadTerrariaData()
  if (props.agentOnline && activeServerKey.value) loadData()
})

onUnmounted(() => {
  window.removeEventListener('ws-message', onWsMessage)
})

watch([activeServerKey, () => props.agentOnline], ([key, online]) => {
  if (key && online) {
    loadData()
    fetchGroups()
  }
  searchQuery.value = ''
  page.value = 1
})

watch(activeTab, () => {
  searchQuery.value = ''
  page.value = 1
})
</script>

<style scoped>
.bl-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: #f8fafc;
}

.bl-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
  box-sizing: border-box;
}

.body-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 14px;
}

.state-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  border-radius: 10px;
  font-size: 14px;
  margin-bottom: 16px;
}

.state-box svg {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.state-empty {
  background: #f8fafc;
  color: #94a3b8;
  border: 1px solid #e2e8f0;
  justify-content: center;
  flex-direction: column;
  padding: 60px 24px;
  text-align: center;
}

.state-empty svg {
  width: 40px;
  height: 40px;
  stroke: #cbd5e1;
  margin-bottom: 8px;
}

.state-loading {
  background: #f8fafc;
  color: #64748b;
  justify-content: center;
  padding: 60px 24px;
  gap: 12px;
}

.state-error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.state-error svg {
  stroke: #ef4444;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  background: #f1f5f9;
  padding: 4px;
  border-radius: 8px;
  width: fit-content;
}

.tab {
  padding: 6px 16px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: 0.15s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab.active {
  background: #fff;
  color: #0f172a;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.tab-count {
  font-size: 11px;
  font-weight: 600;
  background: #e2e8f0;
  color: #64748b;
  padding: 1px 6px;
  border-radius: 10px;
}

.tab.active .tab-count {
  background: #e0e7ff;
  color: #4f46e5;
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 16px;
}

.search-bar svg {
  width: 16px;
  height: 16px;
  stroke: #94a3b8;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 14px;
  color: #0f172a;
  background: transparent;
}

.search-clear {
  background: none;
  border: none;
  cursor: pointer;
  color: #94a3b8;
  font-size: 14px;
  padding: 0;
}

.search-clear:hover {
  color: #475569;
}

.bl-table-wrap {
  overflow-x: auto;
}

.bl-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
}

.bl-table th {
  background: #f8fafc;
  padding: 10px 14px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  border-bottom: 1px solid #e2e8f0;
}

.bl-table td {
  padding: 11px 14px;
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
  vertical-align: middle;
}

.bl-table tr:last-child td {
  border-bottom: none;
}

.item-id {
  font-family: monospace;
  font-size: 13px;
  font-weight: 600;
  color: #4f46e5;
  background: #eff6ff;
  padding: 2px 8px;
  border-radius: 4px;
}

.item-id-empty {
  color: #94a3b8;
  background: #f1f5f9;
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.item-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
  flex-shrink: 0;
}

.groups-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.group-badge {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  color: #1e3a8a;
  background: #dbeafe;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  padding: 2px 8px;
}

.group-badge-empty {
  color: #94a3b8;
}

.empty-row {
  text-align: center;
  color: #94a3b8;
  padding: 40px;
}

.pagination {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  justify-content: center;
}

.page-info {
  font-size: 13px;
  color: #64748b;
}

.toast {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 14px;
  margin-bottom: 16px;
  gap: 12px;
}

.toast-ok {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #bbf7d0;
}

.toast-err {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.toast-close {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: inherit;
  padding: 0;
  margin-left: auto;
}

.btn {
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

.btn svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-sm {
  padding: 7px 16px;
}

.btn-xs {
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 6px;
}

.btn-primary {
  background: #3b82f6;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-outline {
  background: #fff;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-outline:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #9ca3af;
}

.btn-danger {
  background: #ef4444;
  color: #fff;
}

.btn-danger:hover:not(:disabled) {
  background: #dc2626;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-box {
  background: #fff;
  border-radius: 12px;
  width: 460px;
  max-width: 95vw;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  max-height: 90vh;
}

.modal-box-wide {
  width: 680px;
}

.modal-box-sm {
  width: 400px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px 14px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.modal-close {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #94a3b8;
  padding: 0;
}

.modal-close:hover {
  color: #0f172a;
}

.modal-body {
  padding: 20px 22px;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 22px;
  border-top: 1px solid #e2e8f0;
}

.form-field {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 6px;
}

.required {
  color: #ef4444;
}

.form-input {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  color: #0f172a;
  outline: none;
  transition: border-color 0.15s;
}

.form-input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.1);
}

.type-selector {
  display: flex;
  gap: 8px;
}

.type-btn {
  padding: 6px 16px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #64748b;
  font-size: 13px;
  cursor: pointer;
  transition: 0.15s;
}

.type-btn.active {
  background: #eff6ff;
  border-color: #6366f1;
  color: #4f46e5;
  font-weight: 600;
}

.id-search-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 10px;
}

.id-search-wrap svg {
  width: 15px;
  height: 15px;
  stroke: #94a3b8;
}

.id-search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 13px;
}

.id-result-list {
  margin-top: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  max-height: 220px;
  overflow: auto;
}

.id-result-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid #f1f5f9;
  cursor: pointer;
}

.id-result-item:last-child {
  border-bottom: none;
}

.id-result-item:hover {
  background: #f8fafc;
}

.id-result-item.selected {
  background: #eff6ff;
}

.id-result-empty {
  padding: 14px;
  color: #94a3b8;
  text-align: center;
  font-size: 13px;
}

.id-item-img,
.hint-item-img {
  width: 20px;
  height: 20px;
  object-fit: contain;
  flex-shrink: 0;
}

.id-num {
  min-width: 58px;
  font-family: monospace;
  font-size: 12px;
  color: #4f46e5;
}

.id-zhname {
  flex: 1;
}

.id-enname {
  color: #94a3b8;
  font-size: 12px;
}

.id-result-pagination {
  position: sticky;
  bottom: 0;
  background: #fff;
  border-top: 1px solid #e2e8f0;
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 12px;
  color: #64748b;
}

.selected-hint {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 10px;
}

.hint-id-badge {
  font-family: monospace;
  color: #4f46e5;
}

.hint-name {
  flex: 1;
}

.hint-clear {
  background: transparent;
  border: none;
  color: #64748b;
  cursor: pointer;
}

.hint-clear:hover {
  color: #334155;
}

.group-multiselect-wrap {
  position: relative;
}

.group-dropdown {
  position: absolute;
  left: 0;
  right: 0;
  margin-top: 6px;
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.12);
  max-height: 200px;
  overflow: auto;
  z-index: 30;
}

.group-dropdown-item {
  padding: 8px 10px;
  font-size: 13px;
  cursor: pointer;
}

.group-dropdown-item:hover {
  background: #f8fafc;
}

.group-dropdown-item.selected {
  background: #eff6ff;
  color: #312e81;
}

.group-dropdown-empty {
  padding: 12px;
  color: #94a3b8;
  text-align: center;
  font-size: 13px;
}

.group-selected-list {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.group-selected-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 12px;
}

.group-remove-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  color: #6366f1;
  font-size: 12px;
  line-height: 1;
}

.group-selected-empty {
  color: #94a3b8;
  font-size: 13px;
}

.row-actions {
  display: inline-flex;
  gap: 8px;
}

.edit-meta {
  margin: 0 0 10px;
  color: #64748b;
  font-size: 13px;
}

@media (max-width: 860px) {
  .bl-body {
    padding-left: 14px;
    padding-right: 14px;
  }

  .modal-box-wide {
    width: 96vw;
  }
}
</style>
