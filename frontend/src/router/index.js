// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../views/HomePage.vue'
import AccountManager from '../views/AccountManager.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomePage
  },
  {
    path: '/accounts',
    name: 'accounts',
    component: AccountManager
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router