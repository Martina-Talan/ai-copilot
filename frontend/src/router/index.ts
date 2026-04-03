import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import Dashboard from '../views/Dashboard.vue'
import Chat from '../components/ChatForm.vue'
import Home from '../views/Home.vue'
import { useUserStore } from '../store/user';

const routes: RouteRecordRaw[] = [
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  { path: '/dashboard', component: Dashboard, meta: { requiresAuth: true } },
  { 
    path: '/dashboard/:docId', 
    component: Dashboard,
    meta: { requiresAuth: true },
    props: true
  },
  { path: '/chat', component: Chat, meta: { requiresAuth: true } }, 
  { path: '/home', component: Home },
  { path: '/', redirect: '/home' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const store = useUserStore()
  if (to.meta.requiresAuth && !store.token) {
    next('/login')
  } else {
    next()
  }
})

export default router
