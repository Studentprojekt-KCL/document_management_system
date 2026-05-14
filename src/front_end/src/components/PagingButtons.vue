<script setup>
/**
 * Pagination controls component
 */

defineProps({
  currentPage: {
    type: Number,
    required: true
  },

  hasNextPage: {
    type: Boolean,
    required: true
  }
})

const emit = defineEmits(['next', 'previous'])
</script>

<template>
  <div class="pagination">
    <button :disabled="currentPage === 1" @click="emit('previous')">Previous</button>

    <span>Page {{ currentPage }}</span>

    <button :disabled="!hasNextPage" @click="emit('next')">Next</button>
  </div>
</template>

<style scoped>
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  padding: 1rem 0;
}

button {
  padding: 0.5rem 1rem;
}
</style>
