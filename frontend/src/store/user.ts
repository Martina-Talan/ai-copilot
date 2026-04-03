import { defineStore } from 'pinia'

type UserId = string | number | null
type JwtPayload = Partial<{
  sub: string | number
  user_id: string | number
  id: string | number
  email: string
  username: string
}>

const decodeJwt = (token: string): JwtPayload => {
  try {
    const b64 = token.split('.')[1] ?? ''
    return JSON.parse(atob(b64)) as JwtPayload
  } catch {
    return {}
  }
}

export const useUserStore = defineStore('user', {
  state: () => ({
    id: null as UserId,                                 
    token: (typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null),
    email: null as string | null,
    username: null as string | null,
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    userId: (state): string | number | null =>         
      (state.id ?? state.email ?? state.username ?? null),
  },

  actions: {
    init() {
      const storedToken = (typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null)
      if (!storedToken) {
        this.token = null; this.id = null; this.email = null; this.username = null
        return
      }
      this.token = storedToken
      const p = decodeJwt(storedToken)
      this.id = (p.sub ?? p.user_id ?? p.id ?? null) as UserId
      this.email = p.email ?? null
      this.username = p.username ?? null
    },

    setToken(newToken: string) {
      this.token = newToken
      if (typeof localStorage !== 'undefined') localStorage.setItem('token', newToken)
      const p = decodeJwt(newToken)
      this.id = (p.sub ?? p.user_id ?? p.id ?? null) as UserId
      this.email = p.email ?? null
      this.username = p.username ?? null
    },

    logout() {
      this.token = null
      this.id = null
      this.email = null
      this.username = null
      if (typeof localStorage !== 'undefined') localStorage.removeItem('token')
    },
  },

  persist: true,
})
