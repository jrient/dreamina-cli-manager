// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// 页面组件
import Login from '../views/Login.vue'
import HomePage from '../views/HomePage.vue'
import AccountManager from '../views/AccountManager.vue'
import ProjectList from '../views/ProjectList.vue'
import ProjectTasks from '../views/ProjectTasks.vue'
import ProjectMaterials from '../views/ProjectMaterials.vue'
import ProjectSettings from '../views/ProjectSettings.vue'
import AdminEntry from '../views/AdminEntry.vue'
import AdminProjects from '../views/AdminProjects.vue'
import AdminAccounts from '../views/AdminAccounts.vue'
import AdminTasks from '../views/AdminTasks.vue'
import UserManagement from '../views/UserManagement.vue'
import ProjectLayout from '../views/ProjectLayout.vue'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: Login,
    meta: { guest: true }
  },
  {
    path: '/',
    redirect: '/projects'
  },
  {
    path: '/accounts',
    name: 'accounts',
    component: AccountManager,
    meta: { requiresAuth: true }
  },
  {
    path: '/projects',
    name: 'projects',
    component: ProjectList,
    meta: { requiresAuth: true }
  },
  {
    path: '/projects/:id',
    component: ProjectLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: to => ({ name: 'project-tasks', params: to.params }) },
      { path: 'tasks', name: 'project-tasks', component: ProjectTasks, meta: { requiresAuth: true } },
      { path: 'materials', name: 'project-materials', component: ProjectMaterials, meta: { requiresAuth: true } },
      { path: 'settings', name: 'project-settings', component: ProjectSettings, meta: { requiresAuth: true } },
    ]
  },
  {
    path: '/admin',
    name: 'admin',
    component: AdminEntry,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/projects',
    name: 'admin-projects',
    component: AdminProjects,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/accounts',
    name: 'admin-accounts',
    component: AdminAccounts,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/tasks',
    name: 'admin-tasks',
    component: AdminTasks,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/users',
    name: 'admin-users',
    component: UserManagement,
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 如果还没获取用户信息，尝试获取
  if (!authStore.user && !authStore.loading) {
    await authStore.fetchUser()
  }

  // 需要登录的页面
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    return next('/login')
  }

  // 需要管理员的页面
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return next('/')
  }

  // 已登录用户访问登录页，重定向到首页
  if (to.meta.guest && authStore.isLoggedIn) {
    return next('/')
  }

  next()
})

export default router