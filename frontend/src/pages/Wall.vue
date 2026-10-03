<template>
  <div class="wall">
    <h1 class="serif">愿望墙</h1>
    <p class="tag">无顶栏 · 瀑布流 · 点卡片认领 · 按优先级衰减分排序{{ dpd ? `（衰 ${dpd}/天）` : '' }}</p>
    <div class="masonry">
      <article v-for="w in rows" :key="w.id" class="card" @click="$router.push('/wishes/'+w.id)">
        <h3>{{ w.title || '（无标题）' }}</h3>
        <p>{{ w.note }}</p>
        <div class="score-row">
          <span class="score">{{ fmtScore(w.score) }} 分</span>
          <span v-if="w.pinned_score !== null && w.pinned_score !== undefined" class="pin-badge">钉</span>
        </div>
        <span class="tag">{{ w.status }} · 基础 {{ fmtScore(w.base_priority) }} · {{ w.data_quality }}</span>
      </article>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api, fmtScore } from '../api'
const rows = ref([])
const dpd = ref('')
onMounted(async () => {
  rows.value = await api('/wishes')
  const s = await api('/settings')
  dpd.value = s.decay_per_day || ''
})
</script>
<style scoped>
.score-row { display: flex; align-items: center; gap: 8px; margin: 6px 0 2px; }
.score { font-size: 1.15rem; font-weight: 600; color: var(--ink); }
.pin-badge {
  font-size: 11px; line-height: 1; padding: 3px 6px; border-radius: 8px;
  background: var(--rose); color: #fff;
}
</style>
