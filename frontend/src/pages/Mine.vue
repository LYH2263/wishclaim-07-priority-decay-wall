<template>
  <div class="wall">
    <h1 class="serif">我的认领</h1>
    <input v-model="name" @change="load" placeholder="认领人名" />
    <article v-for="w in rows" :key="w.id" class="card" @click="$router.push('/wishes/'+w.id)">
      <h3>{{ w.title }}</h3>
      <div class="score-row">
        <span class="score">{{ fmtScore(w.pinned_score) }} 分</span>
        <span class="pin-badge">认领钉分</span>
      </div>
      <span class="tag">{{ w.status }} · 到期 {{ w.expires_at }}</span>
    </article>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api, fmtScore } from '../api'
const name = ref('访客')
const rows = ref([])
async function load() { rows.value = await api('/mine?claimer=' + encodeURIComponent(name.value)) }
onMounted(load)
</script>
<style scoped>
.score-row { display: flex; align-items: center; gap: 8px; margin: 6px 0 2px; }
.score { font-size: 1.15rem; font-weight: 600; }
.pin-badge {
  font-size: 11px; line-height: 1; padding: 3px 6px; border-radius: 8px;
  background: var(--rose); color: #fff;
}
</style>
