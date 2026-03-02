import { createRouter, createWebHistory } from 'vue-router'
import SearchView from '@/views/SearchView.vue'
import SourcesView from '@/views/SourcesView.vue'
import IntelligenceView from '@/views/IntelligenceView.vue'
import ComplianceView from '@/views/ComplianceView.vue'
import SettingsView from '@/views/SettingsView.vue'
import Login from '../views/Login.vue'

const routes = [
  {
    path: '/',
    name: 'Login',
    component: Login
  },
  {
    path: '/search',
    name: 'Search',
    component: SearchView
  },
  {
    path: '/sources',
    name: 'Sources',
    component: SourcesView
  },
  {
    path: '/intelligence',
    name: 'Intelligence',
    component: IntelligenceView
  },
  {
    path: '/compliance',
    name: 'Compliance',
    component: ComplianceView
  },
  {
    path: '/settings',
    name: 'Settings',
    component: SettingsView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
