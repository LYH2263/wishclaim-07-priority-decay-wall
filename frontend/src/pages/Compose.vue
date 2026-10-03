<template>
  <div class="wall">
    <h1 class="serif">发愿望</h1>
    <input v-model="title" placeholder="标题" />
    <textarea v-model="note" rows="4" placeholder="备注" />
    <label class="tag" for="bp">基础优先级 base_priority（必须 &gt; 0，随创建时长线性衰减）</label>
    <input id="bp" v-model.number="basePriority" type="number" min="0.01" step="1" placeholder="如 100" />
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
const basePriority = ref(100)
const err = ref('')
async function submit() {
  err.value = ''
  if (!(Number(basePriority.value) > 0)) {
    err.value = 'base_priority 必须为正数（> 0）'
    return
  }
  try {
    const r = await api('/wishes', {
      method: 'POST',
      body: JSON.stringify({ title: title.value, note: note.value, base_priority: Number(basePriority.value) }),
    })
    router.push('/wishes/' + r.id)
  } catch (e) { err.value = e.message }
}
</script>
