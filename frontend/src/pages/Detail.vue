<template>
  <div class="wall">
    <h1 class="serif">{{ w.title }}</h1>
    <p>{{ w.note }}</p>
    <p class="tag">状态 {{ w.status }} · 认领人 {{ w.claimer || '—' }}</p>

    <div class="score-box">
      <div class="score-cell">
        <span class="tag">墙序分</span>
        <strong :class="{ pinned: isPinned }">{{ fmtScore(w.score) }}</strong>
        <span v-if="isPinned" class="pin-badge">认领钉分</span>
      </div>
      <div class="score-cell">
        <span class="tag">实时衰减分（若仍开放）</span>
        <strong>{{ fmtScore(w.live_score) }}</strong>
      </div>
      <div class="score-cell">
        <span class="tag">基础优先级</span>
        <strong>{{ fmtScore(w.base_priority) }}</strong>
      </div>
    </div>
    <p v-if="isPinned" class="tag">钉分于认领瞬间冻结；调整衰减参数不会改变此分。</p>

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
import { ref, computed, onMounted } from 'vue'
import { api, fmtScore } from '../api'
const props = defineProps({ id: String })
const w = ref({})
const claimer = ref('访客')
const err = ref('')
const isPinned = computed(() => w.value.pinned_score !== null && w.value.pinned_score !== undefined)
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
.score-box {
  display: flex; gap: 10px; flex-wrap: wrap; margin: 12px 0;
}
.score-cell {
  display: flex; flex-direction: column; gap: 2px;
  background: var(--card); border: 1px solid var(--line);
  border-radius: 14px; padding: 10px 14px; min-width: 150px;
}
.score-cell strong { font-size: 1.4rem; }
.score-cell strong.pinned { color: var(--rose); }
.pin-badge {
  align-self: flex-start; font-size: 11px; padding: 2px 7px; border-radius: 8px;
  background: var(--rose); color: #fff;
}
</style>
