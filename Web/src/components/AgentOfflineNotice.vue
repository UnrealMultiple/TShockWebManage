<template>
  <div :class="['agent-offline-notice', `notice-${type}`, { compact }]">
    <!-- offline: 感叹号圆 -->
    <svg v-if="type === 'offline'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="10"/>
      <line x1="12" y1="8" x2="12" y2="12"/>
      <line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
    <!-- permission: 盾牌锁 -->
    <svg v-else-if="type === 'permission'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
      <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
      <circle cx="12" cy="16" r="1"/>
    </svg>
    <!-- error: X 圆 -->
    <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="10"/>
      <line x1="15" y1="9" x2="9" y2="15"/>
      <line x1="9" y1="9" x2="15" y2="15"/>
    </svg>
    <span>{{ message }}</span>
    <button v-if="showRetry" class="notice-retry-btn" @click="$emit('retry')">{{ retryLabel }}</button>
  </div>
</template>

<script setup>
defineProps({
  message: { type: String, default: 'Agent 未连接，无法读取或保存配置。请先启动服务器。' },
  compact: { type: Boolean, default: false },
  type: {
    type: String,
    default: 'offline',
    validator: (v) => ['offline', 'permission', 'error'].includes(v),
  },
  showRetry: { type: Boolean, default: false },
  retryLabel: { type: String, default: '重试' },
})

defineEmits(['retry'])
</script>

<style scoped>
.agent-offline-notice {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 14px;
  padding: 60px 24px;
  font-size: 14px;
}

.agent-offline-notice svg {
  width: 24px;
  height: 24px;
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

/* ── 类型颜色 ── */
.notice-offline { color: #64748b; }
.notice-offline svg { color: #94a3b8; }

.notice-permission { color: #b45309; }
.notice-permission svg { color: #f59e0b; }

.notice-error { color: #b91c1c; }
.notice-error svg { color: #ef4444; }

/* ── 重试按钮 ── */
.notice-retry-btn {
  padding: 6px 16px;
  border: 1px solid currentColor;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  font-size: 13px;
  cursor: pointer;
  opacity: .8;
  transition: opacity .15s;
}
.notice-retry-btn:hover { opacity: 1; }
</style>
