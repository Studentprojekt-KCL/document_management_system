<script setup>
/**
 * TheSidebar Component
 * Application sidebar for navigation between main sections of the app.
 * Role-based access control to show/hide menu items based on user permissions.
 *
 * @component
 * @example usage:
 * <TheSidebar />
 */

import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Search, Database, BarChart3, ShieldCheck, Settings, Menu, Network } from 'lucide-vue-next'
import { isAdmin } from '@/utils/auth'

const router = useRouter()
const route = useRoute()

const isOpen = ref(false)
const admin = ref(false)

const loadAdminStatus = async () => {
  admin.value = await isAdmin()
}

onMounted(loadAdminStatus)

/* all available items on the sidebar */
const menuItems = [
  { id: 'connections', label: 'Connections', icon: Network, path: '/connections' },
  { id: 'search', label: 'Universal Search', icon: Search, path: '/search' },
  { id: 'sources', label: 'Information Sources', icon: Database, path: '/sources' },
  { id: 'intelligence', label: 'Intelligence', icon: BarChart3, path: '/intelligence' },
  { id: 'compliance', label: 'Security & Compliance', icon: ShieldCheck, path: '/compliance' },
  { id: 'settings', label: 'System Settings', icon: Settings, path: '/settings' }
]

/* Show all itmes fro admin otherwise only search */
const visibleMenuItems = computed(() => {
  const regularUserItems = menuItems.filter((item) => item.id === 'search' || item.id === 'connections')
  return admin.value ? menuItems : regularUserItems
})

/* Compute the active menu item */
const activeItem = computed(() => {
  const found = menuItems.find((item) => item.path === route.path)
  return found ? found.id : 'search'
})

/* Toggle sidebar open/collapse state */
const toggleSidebar = () => {
  isOpen.value = !isOpen.value
}

/* Navigate to the selected menu item's path */
const navigateTo = (path) => {
  router.push(path)
}
</script>

<template>
  <aside :class="['sidebar', { collapsed: !isOpen }]">
    <!-- Top Section with Hamburger -->
    <div class="sidebar-top">
      <button @click="toggleSidebar" class="hamburger-btn">
        <Menu size="20" />
      </button>
    </div>

    <!-- Navigation Menu -->
    <nav class="nav-menu">
      <button
        v-for="item in visibleMenuItems"
        :key="item.id"
        @click="navigateTo(item.path)"
        :class="['nav-item', { active: activeItem === item.id }]"
        :title="item.label"
      >
        <component :is="item.icon" class="nav-icon" />
        <span v-show="isOpen" class="nav-label">{{ item.label }}</span>
      </button>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 280px;
  background: #ffffff;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
  transition: width 0.3s ease;
  border-right: 1px solid #e5e7eb;
}

.sidebar.collapsed {
  width: 80px;
  padding: 1.5rem 0.75rem;
}

.sidebar-top {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.hamburger-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  width: 100%;
  background: transparent;
  cursor: pointer;
  border-radius: 8px;
  color: #6b7280;
}

.hamburger-btn:hover {
  background: #f3f4f6;
  color: #1f2937;
}

.sidebar.collapsed .hamburger-btn {
  justify-content: center;
  padding: 0.875rem;
}

.nav-menu {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 8px;
  text-align: left;
  position: relative;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 0.875rem;
}

.nav-item:hover {
  background: #f3f4f6;
}

.nav-item.active {
  background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%);
  color: white;
}

.nav-icon {
  width: 20px;
  height: 20px;
  stroke-width: 2;
}

.nav-item:not(.active) .nav-icon {
  color: #9ca3af;
}

.nav-item.active .nav-icon {
  color: white;
}

.nav-label {
  font-size: 0.95rem;
  font-weight: 500;
  flex: 1;
}

.nav-item:not(.active) .nav-label {
  color: #6b7280;
}

.nav-item.active .nav-label {
  color: white;
}
</style>
