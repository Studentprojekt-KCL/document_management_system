import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'

//imports for testing
import { hasRole } from './utils/auth'
window.hasRole = hasRole
// end of testing
createApp(App).use(router).mount('#app')
