
<script setup>
// TEXT VIEWER, a component to see text
import { ref, onMounted } from 'vue'
import { loadTxt } from '../utils/api.js'

const text = ref('')

onMounted(async () => {
  try {
    text.value = await loadTxt()
  } catch (err) {
    console.error(err)
  }
})
</script>

<template>
  <pre>{{ text }}</pre>
</template>
