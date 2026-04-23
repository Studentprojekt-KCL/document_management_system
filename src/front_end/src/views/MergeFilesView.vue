<script setup>
/**
 * MergeFilesView.vue - Possibility to merge/summarize files received from the ranker.
 * Metadata displaying and so is fetched from SearchMatches.vue
 * Similar files and the scores are fetched from useAIRerank :)
 */
import { useAIRerank } from '@/composables/aiRerank'
import SearchMatches from '@/components/SearchMatches.vue'

const { aiRerankResults, rerankFilename } = useAIRerank()
</script>

<template>
  <div class="merge-files-view">
    <h1>Merge/Summarize reranked files</h1>
    <div v-if="aiRerankResults.length">
      <h3>Similar to: {{ rerankFilename }}</h3>
      <p class="text-secondary">Select one or more files to merge and summarize their content together with the reranked file.</p>
      <SearchMatches :matches="aiRerankResults" badge-mode="score" />
    </div>
  </div>
</template>

<style scoped>
.merge-files-view {
  padding: 2rem;
}
</style>
