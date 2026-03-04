<script setup>
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const attemptedPath = computed(() => route.fullPath);

const goBack = () => {
	router.back();
};
</script>

<template>
	<section class="not-found-wrapper">
		<article class="not-found-card">
			<p class="error-code">401</p>
			<h1>Unauthorized</h1>
			<p class="text-secondary description">
				You must be logged in to access this page.
			</p>
			<p class="text-secondary path">Requested path: {{ attemptedPath }}</p>

			<div class="actions">
				<button class="btn-primary" @click="goBack">
					Go back to previous page
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
	margin-bottom: 0.5rem;
}

.path {
	font-size: 0.875rem;
	margin-bottom: 1.5rem;
	word-break: break-word;
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
