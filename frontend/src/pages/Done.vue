<template>
  <div class="wall">
    <h1 class="serif">已完成</h1>
    <article v-for="w in rows" :key="w.id" class="card">
      <div class="score-line">
        <span class="score-badge pinned">钉分 {{ fmt(w.score) }}</span>
      </div>
      <h3>{{ w.title }}</h3><p>{{ w.claimer }}</p>
    </article>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const rows = ref([])
function fmt(v) { return Number(v).toFixed(2) }
onMounted(async () => { rows.value = await api('/done') })
</script>
<style scoped>
.score-line { display: flex; justify-content: flex-end; margin-bottom: 4px; }
.score-badge {
  font-size: 12px; padding: 2px 10px; border-radius: 999px; border: 1px solid #f0c3bd;
  background: #fde2df; color: #9c4a44;
}
</style>
