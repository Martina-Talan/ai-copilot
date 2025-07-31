import { defineStore } from 'pinia'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    historyByDoc: {} as Record<number, ChatMessage[]>
  }),
 
  getters: {
    getHistory: (state) => {
      return (documentId: number): ChatMessage[] => {
        return state.historyByDoc[documentId] || []
      }
    }
  },

  actions: {
    addMessage(documentId: number, role: 'user' | 'assistant', content: string) {
      const entry: ChatMessage = {
        role,
        content,
        timestamp: new Date().toISOString()
      }

      if (!this.historyByDoc[documentId]) {
        this.historyByDoc[documentId] = []
      }

      this.historyByDoc[documentId].push(entry)
    },

    clearHistory(documentId: number) {
      this.historyByDoc[documentId] = []
    },
    updateLastAssistantMessage(documentId: number, token: string, index: number) {
      if (this.historyByDoc[documentId] && this.historyByDoc[documentId][index]) {
        this.historyByDoc[documentId][index].content += token
      }
    }
    
  }
})
