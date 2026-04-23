<script setup>
/**
 * MergeFilesView.vue - Possibility to merge/summarize files received from the ranker.
 * Metadata displaying and so is fetched from SearchMatches.vue
 * Similar files and the scores are fetched from useAIRerank :)
 */
import { useAIRerank } from '@/composables/aiRerank'
import SearchMatches from '@/components/SearchMatches.vue'

const { aiRerankResults } = useAIRerank()
</script>

<template>
  <div class="merge-files-view">
    <h1>Merge Files</h1>
    <p class="text-secondary">Functionality to merge and summarize files coming soon...woop</p>
    <div v-if="aiRerankResults.length">
      <h2>Similar Files</h2>
      <SearchMatches :matches="aiRerankResults" badge-mode="score" />
    </div>
  </div>
</template>

<style scoped>
.merge-files-view {
  padding: 2rem;
}
</style>
