import { createRouter, createWebHistory } from 'vue-router'
import SearchView from '@/views/SearchView.vue'
import SourcesView from '@/views/SourcesView.vue'
import IntelligenceView from '@/views/IntelligenceView.vue'
import ComplianceView from '@/views/ComplianceView.vue'
import SettingsView from '@/views/SettingsView.vue'
import LoginView from '../views/LoginView.vue'
import AuthCallbackView from '../views/AuthCallbackView.vue'

const routes = [
  {
    path: '/',
    name: 'Login',
    component: LoginView
  },
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
    meta: { requiresAuth: true}
  },
  {
    path: '/settings',
    name: 'Settings',
    component: SettingsView,
    meta: { requiresAuth: true}
  },
  {
    path: "/auth/callback",
    name: "AuthCallback",
    component: AuthCallbackView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// router guard so that you can't go to a /search without having logged in
router.beforeEach((to)=> {
  const token = sessionStorage.getItem("access_token");
  const isAuthed = !!token;

  //works 
  if (to.meta?.requiresAuth && !isAuthed){
    return {path: '/'};
  } 
  
});

export default router
