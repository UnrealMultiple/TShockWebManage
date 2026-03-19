/**
 * usePlayerList — 封装 player_list WebSocket 请求/响应
 * 同一页面可创建多个实例（各自有独立的 pendingId），互不干扰
 */
import { ref } from 'vue'

export function usePlayerList() {
  const players = ref([])
  const loading = ref(false)
  let pendingId = null
  let timer = null

  /** 向 Agent 请求在线玩家列表 */
  function request(agentKey) {
    if (!agentKey) return
    clearTimeout(timer)
    loading.value = true
    players.value = []
    pendingId = Math.random().toString(36).slice(2)
    window.__tshockSend?.({
      type:      'player_list',
      msg_id:    pendingId,
      timestamp: Date.now(),
      payload:   { agent_key: agentKey },
    })
    timer = setTimeout(() => {
      if (loading.value) { loading.value = false; pendingId = null }
    }, 8000)
    return pendingId
  }

  /**
   * 检查并消费 ws-message 事件；返回 true 表示消息已被此实例消费
   * 组件在自己的 ws-message handler 里调用即可
   */
  function consume(pkt) {
    if (pkt?.type !== 'player_list_resp') return false
    if (pkt.payload?.ref_id !== pendingId) return false
    clearTimeout(timer)
    pendingId = null
    loading.value = false
    if (pkt.payload?.success) players.value = pkt.payload.players || []
    return true
  }

  function reset() {
    clearTimeout(timer)
    pendingId = null
    loading.value = false
    players.value = []
  }

  return { players, loading, request, consume, reset }
}
