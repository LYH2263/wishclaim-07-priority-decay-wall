<template>
  <div class="wall">
    <h1 class="serif">我的认领</h1>
    <input v-model="name" @change="load" placeholder="认领人名" />
    <article v-for="w in rows" :key="w.id" class="card" @click="$router.push('/wishes/'+w.id)">
      <div class="score-line">
        <span class="score-badge" :class="w.score_kind">
          {{ w.score_kind === 'pinned' ? '钉分' : '实时分' }} {{ fmt(w.score) }}
        </span>
      </div>
      <h3>{{ w.title }}</h3>
      <span class="tag">{{ w.status }} · 到期 {{ w.expires_at }}</span>
    </article>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const name = ref('访客')
const rows = ref([])
function fmt(v) { return Number(v).toFixed(2) }
async function load() { rows.value = await api('/mine?claimer=' + encodeURIComponent(name.value)) }
onMounted(load)
</script>
<style scoped>
.score-line { display: flex; justify-content: flex-end; margin-bottom: 4px; }
.score-badge {
  font-size: 12px; padding: 2px 10px; border-radius: 999px; border: 1px solid var(--line);
  background: #fff; color: var(--muted);
}
.score-badge.pinned { background: #fde2df; color: #9c4a44; border-color: #f0c3bd; }
</style>
