import { createRouter, createWebHistory } from 'vue-router'
import Home from './'

const routes = [
  {path: '/home', component: Home},
  { path: '/', redirect: '/home' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
