<script setup>
const props = defineProps({
  matches: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  selected: { type: String, default: '' }
})

const emit = defineEmits(['select'])
</script>

<template>
  <div>
    <h3>Matches</h3>

    <p v-if="loading">Searching…</p>

    <p v-else-if="!matches.length">No matches.</p>

    <ul v-else style="padding-left: 1rem">
      <li v-for="(match, index) in matches" :key="index" style="margin-bottom: 0.5rem">
        <button
          @click="emit('select', match)"
          :style="{
            fontWeight: selected === match.content ? '700' : '400',
            textDecoration: 'underline',
            background: 'none',
            border: 'none',
            cursor: 'pointer'
          }"
        >
          {{ 'Result ' + (index + 1) }}
        </button>
      </li>
    </ul>
  </div>
</template>

