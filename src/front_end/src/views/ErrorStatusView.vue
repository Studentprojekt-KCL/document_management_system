<script setup>
/**
 * ErrorStatusView.vue - A reusable view for displaying error status pages (e.g., 401, 403, 404).
 * A button that either goes back to the previous page or redirects to login if the error is 401 and the user is not logged in.
 */
import { useRouter } from 'vue-router'

/* Props for error code, title, and description. */
const props = defineProps({
  code: {
    type: [String, Number],
    required: true
  },
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    required: true
  }
})

const router = useRouter()

/* Helper functions to determine login status and whether to redirect to login. */
const isUnauthorized = () => Number(props.code) === 401
const shouldGoToLogin = () => isUnauthorized()

/* Function to handle the button click - either go back or redirect to login. */
const goBack = () => {
  if (shouldGoToLogin()) {
    router.push('/')
  } else {
    router.back()
  }
}
</script>

<template>
  <section class="not-found-wrapper">
    <!-- Card displaying the error code, title, description, and action button. -->
    <article class="not-found-card">
      <p class="error-code">{{ code }}</p>
      <h1>{{ title }}</h1>
      <p class="text-secondary description">{{ description }}</p>
      <div class="actions">
        <button class="btn-primary" @click="goBack">
          {{ shouldGoToLogin() ? 'Go to login' : 'Go back to previous page' }}
        </button>
      </div>
    </article>
  </section>
</template>

<style scoped>
.not-found-wrapper {
  min-height: calc(100vh - 64px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.not-found-card {
  width: 100%;
  max-width: 560px;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: 2.5rem 2rem;
  text-align: center;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.06);
}

.error-code {
  font-size: 3.25rem;
  line-height: 1;
  font-weight: 700;
  color: var(--color-accent-dark);
  margin-bottom: 0.5rem;
}

.description {
  margin-bottom: 1.5rem;
}

.actions {
  display: flex;
  justify-content: center;
}

.btn-primary {
  min-width: 150px;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-weight: 600;
  background: var(--color-accent);
  color: #ffffff;
}

.btn-primary:hover {
  background: var(--color-accent-dark);
}
</style>
