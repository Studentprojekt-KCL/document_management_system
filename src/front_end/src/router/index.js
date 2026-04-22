/**
 * Vue Router setup for the frontend.
 *
 * Includes:
 * - Public routes: login (and OAuth callback).
 * - Protected routes: search (auth required) and admin pages (auth + admin role).
 * - Error routes: 401, 403, 404, plus a catch-all redirect to 404.
 *
 * Global guard behavior:
 * - Validates OAuth callback query/state.
 * - Redirects authenticated users away from login to search.
 * - Blocks unauthenticated access to protected routes (401).
 * - Blocks non-admin users from admin routes (403).
 */
import { createRouter, createWebHistory } from 'vue-router'
import ConnectedSourcesView from '@/views/ConnectedSourcesView.vue'
import SearchView from '@/views/SearchView.vue'
import SourcesView from '@/views/SourcesView.vue'
import IntelligenceView from '@/views/IntelligenceView.vue'
import ComplianceView from '@/views/ComplianceView.vue'
import SettingsView from '@/views/SettingsView.vue'
import LoginView from '@/views/LoginView.vue'
import AuthCallbackView from '@/views/AuthCallbackView.vue'
import ErrorStatusView from '@/views/ErrorStatusView.vue'
import { hasRole } from '@/utils/auth'
import { SESSION_KEY_ACCESS_TOKEN, SESSION_KEY_PKCE_VERIFIER } from '@/utils/config'

const routes = [
  /* Public */
  {
    path: '/',
    name: 'Login',
    component: LoginView
  },
  /* OAuth callback route, not reachable for users. */
  {
    path: '/auth/callback',
    name: 'AuthCallback',
    component: AuthCallbackView
  },
  /* Protected */
  {
    path: '/connections',
    name: 'Connections',
    component: ConnectedSourcesView,
    meta: { requiresAuth: true }
  },
  {
    path: '/search',
    name: 'Search',
    component: SearchView,
    meta: { requiresAuth: true }
  },
  /* Admin only routes */
  {
    path: '/sources',
    name: 'Sources',
    component: SourcesView,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/intelligence',
    name: 'Intelligence',
    component: IntelligenceView,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/compliance',
    name: 'Compliance',
    component: ComplianceView,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: SettingsView,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  /* Error routes */
  {
    path: '/404',
    name: 'NotFound',
    component: ErrorStatusView,
    props: {
      code: 404,
      title: 'Not Found',
      description: 'The requested page could not be found.'
    }
  },
  {
    path: '/401',
    name: 'Unauthorized',
    component: ErrorStatusView,
    props: {
      code: 401,
      title: 'Unauthorized',
      description: 'You are not authorized to view this page.'
    }
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: ErrorStatusView,
    props: {
      code: 403,
      title: 'Forbidden',
      description: 'You do not have permission to this page.'
    }
  },
  {
    path: '/:pathMatch(.*)*', // Regex for all unmatched paths
    name: 'NotFoundRedirect', // This route will catch all unmatched paths
    redirect: '/404'
  }
]

/* Vue Router instance with history mode and defined routes. */
const router = createRouter({
  history: createWebHistory(),
  routes
})

/* router guard so that you can't go to protected pages without logging in */
router.beforeEach((to) => {
  const token = localStorage.getItem(SESSION_KEY_ACCESS_TOKEN)
  const isAuthed = !!token

  if (to.name === 'AuthCallback') {
    const hasCode = typeof to.query?.code === 'string' && to.query.code.length > 0
    const hasError = typeof to.query?.error === 'string' && to.query.error.length > 0
    const hasPkceVerifier = !!localStorage.getItem(SESSION_KEY_PKCE_VERIFIER)

    if (!hasError && (!hasCode || !hasPkceVerifier)) {
      return { path: '/401' }
    }
    return true
  }

  if (to.name === 'Login' && isAuthed) {
    return { path: '/search' }
  }

  if (to.meta?.requiresAuth && !isAuthed) {
    return { path: '/401' }
  }

  /* Admin only route */
  if (to.meta?.requiresAdmin && !hasRole('admin')) {
    return { path: '/403' }
  }

  return true
})

export default router
