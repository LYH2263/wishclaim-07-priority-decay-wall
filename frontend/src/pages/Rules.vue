<template>
  <div class="wall">
    <h1 class="serif">规则</h1>
    <div class="formula card-static">
      <div class="tag">优先级衰减排墙（公式与墙排序同源）</div>
      <p class="formula-line">{{ rules.priority_formula }}</p>
      <p class="tag">{{ rules.priority_decay }}</p>
      <p class="tag">{{ rules.priority_pinned }}</p>
      <p class="tag">{{ rules.priority_param }}</p>
      <p class="tag">{{ rules.base_priority }}</p>
      <p class="tag">{{ rules.wall_order }}</p>
    </div>
    <ul>
      <li v-for="(v,k) in other" :key="k"><strong>{{ k }}</strong>：{{ v }}</li>
    </ul>
  </div>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
const rules = ref({})
const PRIORITY_KEYS = ['priority_formula', 'priority_decay', 'priority_pinned',
  'priority_param', 'base_priority', 'wall_order']
const other = computed(() =>
  Object.fromEntries(Object.entries(rules.value).filter(([k]) => !PRIORITY_KEYS.includes(k))))
onMounted(async () => { rules.value = await api('/rules') })
</script>
<style scoped>
.card-static {
  background: var(--card); border: 1px solid var(--line); border-radius: 18px;
  padding: 16px; margin: 0 0 18px;
}
.formula-line {
  font-size: 1.15rem; font-family: "Instrument Serif", serif; margin: 8px 0;
  color: #9c4a44;
}
</style>
