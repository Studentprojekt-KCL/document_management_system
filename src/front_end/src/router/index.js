import { createRouter, createWebHistory } from 'vue-router'
import SearchView from '@/views/SearchView.vue'
import SourcesView from '@/views/SourcesView.vue'
import IntelligenceView from '@/views/IntelligenceView.vue'
import ComplianceView from '@/views/ComplianceView.vue'
import SettingsView from '@/views/SettingsView.vue'
import LoginView from '../views/LoginView.vue'
import AuthCallbackView from '../views/AuthCallbackView.vue'
import { hasRole } from '../utils/auth'

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
    meta: { requiresAuth: true}
  },
  {
    path: '/intelligence',
    name: 'Intelligence',
    component: IntelligenceView,
    meta: { requiresAuth: true}
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
  
  /*
  path: "/error",
  name: "Error",
  component: ErrorView, // You would need to create an ErrorView.vue for this to work
  */
  {
    path: '/:pathMatch(.*)*', // Regex for all unmatched paths
    name: 'NotFoundRedirect', // This route will catch all unmatched paths
    redirect: () => {
      const token = sessionStorage.getItem('access_token') 
      return token ? '/search' : '/' // later return token ? '/error' : '/'
      // I (Emma) think that if anything else is typed in the URL, it should redirect to an error page. 
      // But for now, it just redirects to the login page if not logged in, and the search page if logged in.
    }
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
      return { path: '/' }
    }
    return true
  }

  if (to.name === 'Login' && isAuthed) {
    return { path: '/search' } // may be changed to error page later.
  }

  if (to.meta?.requiresAuth && !isAuthed) {
    return { path: '/' }
  }

  // admin only route
  if (to.meta?.requiresAdmin && !hasRole("admin")){
    return {path: "/search"}
  }

  return true
})

export default router
