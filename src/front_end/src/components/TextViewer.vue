<script setup>
import { ref, onMounted } from "vue"

const txt = ref("")

async function loadTxt() {
  const res = await fetch("http://localhost:8000/txt-content")

  if (!res.ok) {
    throw new Error(`Failed: ${res.status}`)
  }

  txt.value = await res.text()
}

onMounted(loadTxt)
</script>

<template>
  <pre>{{ txt }}</pre>
</template>