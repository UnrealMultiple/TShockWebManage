<template>
  <div class="placeholder-page">
    <PageHeader :title="title" heading-tag="h1" />
    <div class="placeholder-card">
      <div class="placeholder-icon">🚧</div>
      <p class="placeholder-desc">该功能正在开发中，敬请期待。</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'

const route = useRoute()
const title = computed(() => route.meta?.title || '功能开发中')
</script>

<style scoped>
.placeholder-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f1f5f9;
}
.placeholder-card {
  margin: auto;
  text-align: center;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 48px 64px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
.placeholder-icon { font-size: 48px; margin-bottom: 16px; }
.placeholder-desc {
  font-size: 14px;
  color: #94a3b8;
  margin: 0;
}
</style>
