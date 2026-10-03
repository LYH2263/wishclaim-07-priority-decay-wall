<template>
  <div class="wall">
    <h1 class="serif">已完成</h1>
    <article v-for="w in rows" :key="w.id" class="card" @click="$router.push('/wishes/'+w.id)">
      <h3>{{ w.title }}</h3>
      <p class="tag">{{ w.claimer }} · 钉分 {{ fmtScore(w.pinned_score) }}</p>
    </article>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api, fmtScore } from '../api'
const rows = ref([])
onMounted(async () => { rows.value = await api('/done') })
</script>
