import { defineStore } from 'pinia'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  sources?: { pageNumber: number }[]
}

export const useChatStore = defineStore('chat', {
  state: () => ({ historyByKey: {} as Record<string, ChatMessage[]> }),
  getters: {
    getHistory: (state) => (documentId: string, userId?: string|number) =>
      state.historyByKey[`${userId ?? 'anon'}::${documentId}`] || [],
  },
  actions: {
    replaceHistory(documentId: string, userId: string|number|undefined, msgs: ChatMessage[]) {
      this.historyByKey[`${userId ?? 'anon'}::${documentId}`] = msgs.slice()
    },
    addMessage(documentId: string, role: 'user'|'assistant', content: string, sources?: any[], userId?: string|number) {
      const k = `${userId ?? 'anon'}::${documentId}`
      ;(this.historyByKey[k] ||= []).push({ role, content, timestamp: new Date().toISOString(), sources })
    },
    clearHistory(documentId: string, userId?: string|number) {
      delete this.historyByKey[`${userId ?? 'anon'}::${documentId}`]
    },
    resetAll() { this.historyByKey = {} },
  },
  persist: false,
})