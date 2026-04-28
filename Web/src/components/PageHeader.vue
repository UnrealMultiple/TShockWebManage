<template>
  <header class="page-shell-header">
    <div class="page-shell-header-left">
      <component :is="headingTag" class="page-shell-title">{{ title }}</component>
      <span v-if="subtitle" class="page-shell-subtitle">{{ subtitle }}</span>
      <slot name="meta"></slot>
    </div>
    <div v-if="$slots.actions" class="page-shell-actions">
      <slot name="actions"></slot>
    </div>
  </header>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  headingTag: { type: String, default: 'h2' },
})
</script>

<style scoped>
.page-shell-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 28px 16px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 12px;
}

.page-shell-header-left,
.page-shell-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.page-shell-actions {
  gap: 8px;
}

.page-shell-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.page-shell-subtitle {
  font-size: 12px;
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  padding: 2px 8px;
  border-radius: 20px;
  box-sizing: border-box;
}
</style>
