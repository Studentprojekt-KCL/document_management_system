<script setup>
/**
 * MergeFilesView.vue - Possibility to merge/summarize files received from the ranker.
 */
import { useAIRerank } from '@/composables/aiRerank'

const { aiRerankResults } = useAIRerank()
</script>

<template>
  <div class="merge-files-view">
    <h1>Merge Files</h1>
    <p class="text-secondary">Functionality to merge and summarize files coming soon...woop</p>
    <div v-if="aiRerankResults.length">
      <h2>Similar Files</h2>
      <ul>
        <li v-for="result in aiRerankResults" :key="result.pointer">
          {{ result.rank }}. {{ result.name }} - Score: {{ result.scorePercent }}
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.merge-files-view {
  padding: 2rem;
}
</style>
