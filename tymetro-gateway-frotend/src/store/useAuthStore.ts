import { defineStore } from 'pinia'

export const useAuthStore = defineStore('useAuthStore', {
  state: () => ({
    accessToken: '',
    isAuthenticated: false,
  }),
  actions: {
    setToken(token: string) {
      this.accessToken = token
      this.isAuthenticated = true
    },
    clearToken() {
      this.accessToken = ''
      this.isAuthenticated = false
    },
  },
  persist: {
    key: 'useAuthStore',
    storage: localStorage,
    paths: ['isAuthenticated'],
  },
})
