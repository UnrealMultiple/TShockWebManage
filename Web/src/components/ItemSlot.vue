<template>
  <img v-if="item.net_id" :src="itemImage(item.net_id)"
       class="slot-img"
       :title="item.name || ('#' + item.net_id)"
       @error="e => e.target.style.display='none'" />
  <span v-if="item.net_id && item.stack > 1" class="slot-stack">{{ item.stack }}</span>
  <span v-if="!item.net_id" class="slot-empty">—</span>
</template>

<script setup>
import { itemImage } from '@/utils/assetPath.js'

defineProps({ item: { type: Object, required: true } })
</script>

<style scoped>
.slot-img {
  width: 38px;
  height: 38px;
  object-fit: contain;
  image-rendering: pixelated;
  image-rendering: crisp-edges;
}
.slot-stack {
  position: absolute;
  bottom: 1px;
  right: 2px;
  font-size: .6rem;
  font-weight: 700;
  color: #0f172a;
  background: rgba(255, 255, 255, .85);
  border-radius: 3px;
  padding: 0 2px;
  line-height: 1.2;
  pointer-events: none;
}
.slot-empty {
  font-size: .7rem;
  color: #cbd5e1;
}
</style>
