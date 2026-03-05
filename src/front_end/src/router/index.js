import { createRouter, createWebHistory } from 'vue-router'
import SearchView from '@/views/SearchView.vue'
import SourcesView from '@/views/SourcesView.vue'
import IntelligenceView from '@/views/IntelligenceView.vue'
import ComplianceView from '@/views/ComplianceView.vue'
import SettingsView from '@/views/SettingsView.vue'
import LoginView from '@/views/LoginView.vue'
import AuthCallbackView from '@/views/AuthCallbackView.vue'
import NotFoundView from '@/views/errors/NotFoundView.vue'
import UnauthorizedView from '@/views/errors/UnauthorizedView.vue'
import ForbiddenView from '@/views/errors/ForbiddenView.vue'
import { hasRole } from '@/utils/auth'

const routes = [
  // Public ~ish
  {
    path: '/',
    name: 'Login',
    component: LoginView
  },
  {
    path: "/auth/callback",
    name: "AuthCallback",
    component: AuthCallbackView
  },
  // Requires Auth
  {
    path: '/search',
    name: 'Search',
    component: SearchView,
    meta: { requiresAuth: true}
  },
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
  {
    path: '/404',
    name: 'NotFound',
    component: NotFoundView
  },
  {
    path: '/401',
    name: 'Unauthorized',
    component: UnauthorizedView
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: ForbiddenView
  },
  {
    path: '/:pathMatch(.*)*', // Regex for all unmatched paths
    name: 'NotFoundRedirect', // This route will catch all unmatched paths
    redirect: '/404'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// router guard so that you can't go to protected pages without logging in
router.beforeEach((to) => {
  const token = sessionStorage.getItem('access_token')
  const isAuthed = !!token

  if (to.name === 'AuthCallback') {
    const hasCode = typeof to.query?.code === 'string' && to.query.code.length > 0
    const hasError = typeof to.query?.error === 'string' && to.query.error.length > 0
    const hasPkceVerifier = !!sessionStorage.getItem('pkce_verifier')

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

  // admin only route
  if (to.meta?.requiresAdmin && !hasRole("admin")){
    return {path: "/403"}
  }

  return true
})

export default router
