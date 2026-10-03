<template>
  <div class="wall">
    <h1 class="serif">{{ w.title }}</h1>
    <p>{{ w.note }}</p>
    <p class="tag">状态 {{ w.status }} · 认领人 {{ w.claimer || '—' }}</p>

    <div class="score-panel">
      <div class="score-cell">
        <span class="tag">墙序分（{{ w.score_kind === 'pinned' ? '钉分 · 冻结' : '实时分 · 随时间衰减' }}）</span>
        <strong :class="{ pinned: w.score_kind === 'pinned' }">{{ fmt(w.score) }}</strong>
      </div>
      <div class="score-cell">
        <span class="tag">认领瞬间钉分快照</span>
        <strong class="pinned">{{ w.pinned_score != null ? fmt(w.pinned_score) : '—' }}</strong>
      </div>
      <div class="score-cell">
        <span class="tag">基础分 base_priority</span>
        <strong>{{ w.base_priority != null ? Number(w.base_priority).toFixed(2) : '—' }}</strong>
      </div>
    </div>
    <p class="tag">
      公式 score = max(0, base_priority − decay_per_day × 已创建天数)；
      claimed/fulfilled 与墙同读钉分，两处分值一致即可核对。
    </p>

    <p v-if="err" class="err">{{ err }}</p>
    <input v-model="claimer" placeholder="你的名字" />
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button @click="claim">认领锁定</button>
      <button class="ghost" @click="release">释放</button>
      <button class="ghost" @click="fulfill">核销完成</button>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const props = defineProps({ id: String })
const w = ref({})
const claimer = ref('访客')
const err = ref('')
function fmt(v) { return Number(v).toFixed(2) }
async function load() { w.value = await api('/wishes/' + props.id) }
async function claim() {
  err.value=''; try { await api('/wishes/'+props.id+'/claim',{method:'POST',body:JSON.stringify({claimer:claimer.value})}); await load() } catch(e){ err.value=e.message }
}
async function release() {
  err.value=''; try { await api('/wishes/'+props.id+'/release',{method:'POST',body:'{}'}); await load() } catch(e){ err.value=e.message }
}
async function fulfill() {
  err.value=''; try { await api('/wishes/'+props.id+'/fulfill',{method:'POST',body:'{}'}); await load() } catch(e){ err.value=e.message }
}
onMounted(load)
</script>
<style scoped>
.score-panel {
  display: flex; gap: 10px; margin: 12px 0;
}
.score-cell {
  flex: 1; background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  padding: 10px 14px; display: flex; flex-direction: column; gap: 4px;
}
.score-cell strong { font-size: 1.5rem; font-family: "Instrument Serif", serif; }
.pinned { color: #9c4a44; }
</style>
