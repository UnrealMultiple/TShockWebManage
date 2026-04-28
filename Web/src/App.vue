<template>
  <FeedbackHost />
  <router-view v-slot="{ Component }">
    <transition name="fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup>
import FeedbackHost from '@/components/FeedbackHost.vue'
</script>
