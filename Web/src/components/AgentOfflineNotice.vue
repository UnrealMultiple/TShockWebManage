<template>
  <div :class="['agent-offline-notice', { compact }]">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="10"/>
      <line x1="12" y1="8" x2="12" y2="12"/>
      <line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
    <span>{{ message }}</span>
  </div>
</template>

<script setup>
defineProps({
  message: { type: String, default: 'Agent 未连接，无法读取或保存配置。请先启动服务器。' },
  compact: { type: Boolean, default: false },
})
</script>

<style scoped>
.agent-offline-notice {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 60px 24px;
  color: #64748b;
  font-size: 14px;
}

.agent-offline-notice svg {
  width: 24px;
  height: 24px;
  color: #94a3b8;
  flex-shrink: 0;
}

.agent-offline-notice.compact {
  justify-content: flex-start;
  gap: 10px;
  padding: 8px 0;
  font-size: .84rem;
}

.agent-offline-notice.compact svg {
  width: 18px;
  height: 18px;
}
</style>
