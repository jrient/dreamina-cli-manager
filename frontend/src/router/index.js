// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../views/HomePage.vue'
import AccountManager from '../views/AccountManager.vue'
import ProjectList from '../views/ProjectList.vue'
import ProjectTasks from '../views/ProjectTasks.vue'
import ProjectMaterials from '../views/ProjectMaterials.vue'
import AdminEntry from '../views/AdminEntry.vue'
import AdminProjects from '../views/AdminProjects.vue'
import AdminAccounts from '../views/AdminAccounts.vue'
import AdminTasks from '../views/AdminTasks.vue'

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
  },
  {
    path: '/projects',
    name: 'projects',
    component: ProjectList
  },
  {
    path: '/projects/:id/tasks',
    name: 'project-tasks',
    component: ProjectTasks
  },
  {
    path: '/projects/:id/materials',
    name: 'project-materials',
    component: ProjectMaterials
  },
  {
    path: '/admin',
    name: 'admin',
    component: AdminEntry
  },
  {
    path: '/admin/projects',
    name: 'admin-projects',
    component: AdminProjects
  },
  {
    path: '/admin/accounts',
    name: 'admin-accounts',
    component: AdminAccounts
  },
  {
    path: '/admin/tasks',
    name: 'admin-tasks',
    component: AdminTasks
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router