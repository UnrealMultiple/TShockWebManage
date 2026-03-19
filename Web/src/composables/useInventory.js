/**
 * useInventory — 封装背包查看/编辑的 WebSocket 请求/响应
 * 同一页面可多次调用，各自维护独立状态。
 *
 * 用法：
 *   const inv = useInventory()
 *   inv.openInventory(charName, agentKey)
 *   // 在 ws-message handler 里：
 *   inv.consumeWsMessage(pkt)
 */
import { ref } from 'vue'

export function useInventory() {
  const invVisible    = ref(false)
  const invUsername   = ref('')
  const invLoading    = ref(false)
  const invError      = ref('')
  const invSlots      = ref([])
  const invHealth     = ref(0)
  const invMaxHealth  = ref(0)
  const invMana       = ref(0)
  const invMaxMana    = ref(0)
  const invIsOnline   = ref(false)
  const invSscEnabled = ref(false)
  const invSaving     = ref(false)

  let pendingInvId  = null
  let pendingSaveId = null
  let timer         = null

  function openInventory(name, agentKey) {
    invVisible.value    = true
    invUsername.value   = name
    invLoading.value    = true
    invError.value      = ''
    invSlots.value      = []
    invIsOnline.value   = false
    invSscEnabled.value = false
    clearTimeout(timer)
    pendingInvId = `inv-${Date.now()}`
    window.__tshockSend?.({
      type:      'get_inventory',
      msg_id:    pendingInvId,
      timestamp: Date.now(),
      payload:   { agent_key: agentKey, username: name },
    })
    timer = setTimeout(() => {
      if (invLoading.value) {
        invLoading.value = false
        invError.value   = '请求超时，请检查 Agent 连接'
        pendingInvId     = null
      }
    }, 10000)
  }

  function handleSaveInventory(slotMap, agentKey) {
    invSaving.value = true
    const slots = Object.values(slotMap).sort((a, b) => a.index - b.index)
    pendingSaveId = `sinv-${Date.now()}`
    window.__tshockSend?.({
      type:      'save_inventory',
      msg_id:    pendingSaveId,
      timestamp: Date.now(),
      payload:   { agent_key: agentKey, username: invUsername.value, slots },
    })
  }

  /**
   * 在组件的 ws-message handler 里调用。
   * 返回 true 表示此包已被消费。
   */
  function consumeWsMessage(pkt) {
    if (pkt.type === 'get_inventory_resp') {
      const p = pkt.payload || {}
      if (p.ref_id !== pendingInvId) return false
      clearTimeout(timer)
      pendingInvId     = null
      invLoading.value = false
      if (p.success) {
        invSlots.value      = p.slots      || []
        invHealth.value     = p.health     || 0
        invMaxHealth.value  = p.max_health || 0
        invMana.value       = p.mana       || 0
        invMaxMana.value    = p.max_mana   || 0
        invIsOnline.value   = !!p.is_online
        invSscEnabled.value = !!p.ssc_enabled
      } else {
        invError.value = p.msg || '加载背包数据失败'
      }
      return true
    }

    if (pkt.type === 'save_inventory_resp') {
      const p = pkt.payload || {}
      if (p.ref_id !== pendingSaveId) return false
      pendingSaveId   = null
      invSaving.value = false
      alert(p.success ? (p.msg || '保存成功') : ('保存失败: ' + (p.msg || '未知错误')))
      return true
    }

    return false
  }

  return {
    invVisible, invUsername, invLoading, invError,
    invSlots, invHealth, invMaxHealth, invMana, invMaxMana,
    invIsOnline, invSscEnabled, invSaving,
    openInventory, handleSaveInventory, consumeWsMessage,
  }
}
