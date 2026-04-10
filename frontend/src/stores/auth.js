// frontend/src/stores/auth.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

axios.defaults.withCredentials = true

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.is_admin || false)

  async function fetchUser() {
    try {
      const response = await axios.get('/api/auth/me')
      user.value = response.data
      return true
    } catch (err) {
      user.value = null
      return false
    }
  }

  async function login(username, password) {
    const response = await axios.post('/api/auth/login', { username, password })
    user.value = response.data.user
    return response.data
  }

  async function logout() {
    try {
      await axios.post('/api/auth/logout')
    } catch (err) {
      // ignore
    }
    user.value = null
  }

  return {
    user,
    loading,
    isLoggedIn,
    isAdmin,
    fetchUser,
    login,
    logout
  }
})