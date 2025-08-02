import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    email: null as string | null,
    username: null as string | null,
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
  },
  actions: {
    init() {
      const storedToken = localStorage.getItem('token');
      if (storedToken) {
        this.token = storedToken;
        try {
          const payload = JSON.parse(atob(storedToken.split('.')[1]));
          this.email = payload.email || null;
          this.username = payload.username || null;
        } catch (e) {
          this.email = null;
          this.username = null;
        }
      }
    },    
    setToken(newToken: string) {
      this.token = newToken
      localStorage.setItem('token', newToken)

      try {
        const payload = JSON.parse(atob(newToken.split('.')[1]))
        this.email = payload.email || null
        this.username = payload.username || null
      } catch (e) {
        this.email = null
        this.username = null
      }
    },
    logout() {
      this.token = null
      this.email = null
      this.username = null
      localStorage.removeItem('token')
    },
  },
})
