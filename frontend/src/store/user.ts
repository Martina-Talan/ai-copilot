import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    email: null as string | null,
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
  },
  actions: {
    setToken(newToken: string) {
      this.token = newToken
      localStorage.setItem('token', newToken)

      const payload = JSON.parse(atob(newToken.split('.')[1]))
      this.email = payload.email || null
    },
    logout() {
      this.token = null
      this.email = null
      localStorage.removeItem('token')
    },
  },
})
