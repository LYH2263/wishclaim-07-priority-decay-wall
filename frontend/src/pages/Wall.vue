<template>
  <div class="wall">
    <h1 class="serif">愿望墙</h1>
    <p class="tag">无顶栏 · 按优先级分降序 · 点卡片认领 · open/released 实时衰减，已认领展示钉分</p>
    <div class="masonry">
      <article v-for="w in rows" :key="w.id" class="card" @click="$router.push('/wishes/'+w.id)">
        <div class="score-line">
          <span class="score-badge" :class="w.score_kind">
            {{ w.score_kind === 'pinned' ? '钉分' : '实时分' }} {{ fmt(w.score) }}
          </span>
        </div>
        <h3>{{ w.title || '（无标题）' }}</h3>
        <p>{{ w.note }}</p>
        <span class="tag">{{ w.status }} · base {{ w.base_priority }} · {{ w.data_quality }}</span>
      </article>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const rows = ref([])
function fmt(v) { return Number(v).toFixed(2) }
onMounted(async () => { rows.value = await api('/wishes') })
</script>
<style scoped>
.score-line { display: flex; justify-content: flex-end; margin-bottom: 4px; }
.score-badge {
  font-size: 12px; padding: 2px 10px; border-radius: 999px; border: 1px solid var(--line);
  background: #fff; color: var(--muted);
}
.score-badge.pinned { background: #fde2df; color: #9c4a44; border-color: #f0c3bd; }
</style>
