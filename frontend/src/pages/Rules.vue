<template>
  <div class="wall">
    <h1 class="serif">规则</h1>
    <ul>
      <li v-for="r in items" :key="r.key">
        <strong>{{ r.label }}</strong>：<span :class="{ formula: r.key === 'priority_formula' }">{{ r.value }}</span>
      </li>
    </ul>
  </div>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
const rules = ref({})
const LABELS = {
  mutex: '互斥认领',
  ttl: '超时释放',
  fulfill: '核销',
  priority_formula: '优先级公式',
  priority_decay: '衰减方式',
  priority_pin: '认领钉分',
  priority_param: '参数调整',
  base_priority_rule: '发布门槛',
}
const ORDER = ['priority_formula', 'priority_decay', 'priority_pin', 'priority_param',
  'base_priority_rule', 'mutex', 'ttl', 'fulfill']
const items = computed(() =>
  Object.keys(rules.value)
    .sort((a, b) => ORDER.indexOf(a) - ORDER.indexOf(b))
    .map(key => ({ key, label: LABELS[key] || key, value: rules.value[key] }))
)
onMounted(async () => { rules.value = await api('/rules') })
</script>
<style scoped>
.formula {
  font-family: Georgia, 'Instrument Serif', serif;
  font-size: 1.08rem;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 2px 8px;
  white-space: nowrap;
}
</style>
