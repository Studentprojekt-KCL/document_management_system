<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { 
  Search, 
  Database, 
  BarChart3, 
  ShieldCheck, 
  Settings,
  Menu
} from 'lucide-vue-next'

// TESTING
import { hasRole } from '../utils/auth'

const router = useRouter()
const route = useRoute()
const isOpen = ref(true)

const menuItems = [
  { id: 'search', label: 'Universal Search', icon: Search, path: '/search' },
  { id: 'sources', label: 'Information Sources', icon: Database, path: '/sources' },
  { id: 'intelligence', label: 'Intelligence', icon: BarChart3, path: '/intelligence' },
  { id: 'compliance', label: 'Security & Compliance', icon: ShieldCheck, path: '/compliance' },
  { id: 'settings', label: 'System Settings', icon: Settings, path: '/settings' }
]

const isAdmin = computed(() => hasRole('admin'))
const visibleMenuItems = computed(() => {
  if (isAdmin.value) {
    return menuItems
  }
  else {
    return menuItems.filter(item => item.id === 'search')
  }
})


const activeItem = computed(() => {
  const currentPath = route.path
  const found = menuItems.find(item => item.path === currentPath)
  return found ? found.id : 'search'
})

const toggleSidebar = () => {
  isOpen.value = !isOpen.value
}

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
        <div v-if="activeItem === item.id && isOpen" class="nav-indicator" />
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
  justify-content: center;
}

.hamburger-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
  color: #6b7280;
  transition: color 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.hamburger-btn:hover {
  color: #1f2937;
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
  transition: all 0.2s;
  text-align: left;
  position: relative;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 0.875rem;
}

.nav-item:hover {
  background: #F3F4F6;
}

.nav-item.active {
  background: linear-gradient(135deg, #5B21B6 0%, #7C3AED 100%);
  color: white;
}

.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  stroke-width: 2;
}

.nav-item:not(.active) .nav-icon {
  color: #9CA3AF;
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
  color: #6B7280;
}

.nav-item.active .nav-label {
  color: white;
}

.nav-indicator {
  width: 6px;
  height: 6px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 50%;
}
</style>
