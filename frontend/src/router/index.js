// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import SubmitTask from '../views/SubmitTask.vue'
import TaskList from '../views/TaskList.vue'
import AccountManager from '../views/AccountManager.vue'

const routes = [
  { path: '/', component: SubmitTask },
  { path: '/tasks', component: TaskList },
  { path: '/accounts', component: AccountManager },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})