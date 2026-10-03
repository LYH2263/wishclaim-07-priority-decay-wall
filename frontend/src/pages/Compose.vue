<template>
  <div class="wall">
    <h1 class="serif">发愿望</h1>
    <input v-model="title" placeholder="标题" />
    <textarea v-model="note" rows="4" placeholder="备注" />
    <label class="tag">基础优先级 base_priority（必须为正数 &gt; 0，≤0 会被拒发）</label>
    <input v-model.number="basePriority" type="number" step="0.1" min="0.000001" placeholder="10" />
    <p class="tag">
      发布后 open 状态按 score = max(0, base_priority − decay_per_day × 已创建天数) 线性衰减；
      被认领瞬间分数钉死为快照。
    </p>
    <p v-if="err" class="err">{{ err }}</p>
    <button @click="submit">发布</button>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
const router = useRouter()
const title = ref('')
const note = ref('')
const basePriority = ref(10)
const err = ref('')
async function submit() {
  err.value = ''
  try {
    const r = await api('/wishes', {
      method: 'POST',
      body: JSON.stringify({ title: title.value, note: note.value, base_priority: basePriority.value }),
    })
    router.push('/wishes/' + r.id)
  } catch (e) { err.value = e.message }
}
</script>
