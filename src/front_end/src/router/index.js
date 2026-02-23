import { createRouter, createWebHistory } from 'vue-router'
import Search from '@/views/Search.vue'
import Sources from '@/views/Sources.vue'
import Intelligence from '@/views/Intelligence.vue'
import Compliance from '@/views/Compliance.vue'
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
    component: Search
  },
  {
    path: '/sources',
    name: 'Sources',
    component: Sources
  },
  {
    path: '/intelligence',
    name: 'Intelligence',
    component: Intelligence
  },
  {
    path: '/compliance',
    name: 'Compliance',
    component: Compliance
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
