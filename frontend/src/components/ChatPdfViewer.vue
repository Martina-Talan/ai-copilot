<template>
    <div class="container-fluid chat-pdf-layout">
      <div class="row">
        <ChatPanel
          ref="chatPanelRef"
          :history="history"
          :user-initial="userInitial"
          :loading="loading"
          :is-streaming="isStreaming"
          :answer="answer"
          :error="error"
          @back="$emit('back')"
          @ask="handleAsk"
        />
  
        <PdfPanel
          :pdf-pages="pdfPages"
          :set-canvas-ref="setCanvasRef"
        />
      </div>
    </div>
  </template>
  
  <script setup lang="ts">
  import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import ChatPanel from './ChatPanel.vue'
  import PdfPanel from './PdfPanel.vue'
  import { useChatStore } from '../store/chat'
  import { useUserStore } from '../store/user'
  import { usePdfViewer } from '../composables/usePdfViewer'
  import { useChatSocket } from '../composables/useChatSocket'
  
  const props = defineProps<{
    documentId: string
    path: string | null
  }>()
  
  defineEmits<{
    (e: 'back'): void
  }>()
  
  const userStore = useUserStore()
  const chatStore = useChatStore()
  
  const userInitial = computed(() => (userStore.username || '').charAt(0).toUpperCase())
  const history = computed(() => chatStore.getHistory(props.documentId, userStore.userId))
  
  const chatPanelRef = ref<InstanceType<typeof ChatPanel> | null>(null)
  
  const scrollToBottom = () => {
    chatPanelRef.value?.scrollToBottom()
  }
  
  const {
    pdfPages,
    pdfInstance,
    setCanvasRef,
    renderPage,
    clearAllHighlights,
    scrollToPage,
    loadPdf,
  } = usePdfViewer()
  
  const addAssistantMessage = (content: string, sources?: { pageNumber: number }[]) => {
    chatStore.addMessage(props.documentId, 'assistant', content, sources as any, userStore.userId)
  }
  
  const {
    answer,
    error,
    loading,
    isStreaming,
    connectWebSocket,
    disconnectWebSocket,
    sendQuestion,
  } = useChatSocket({
    documentId: props.documentId,
    renderPage,
    clearAllHighlights,
    scrollToPage,
    getPdfInstance: () => pdfInstance.value,
    addAssistantMessage,
    scrollToBottom,
  })
  
  const handleAsk = async (question: string) => {
    if (!question.trim() || !props.documentId) return
  
    chatStore.addMessage(props.documentId, 'user', question, undefined, userStore.userId)
    await sendQuestion(question)
  }
  
  onMounted(async () => {
    connectWebSocket()
  
    try {
      const response = await fetch(`/chat/${props.documentId}`, {
        headers: { Authorization: `Bearer ${userStore.token}` },
      })
  
      if (response.ok) {
        const rows = await response.json()
        for (const msg of rows) {
          chatStore.addMessage(
            props.documentId,
            msg.role,
            msg.content,
            msg.sources,
            userStore.userId
          )
        }
      }
    } catch (err) {
      console.error('Error loading chat history:', err)
    }
  })
  
  onBeforeUnmount(() => {
    disconnectWebSocket()
  })
  
  watch(
    () => props.path,
    newPath => {
      if (newPath) loadPdf(newPath)
    },
    { immediate: true }
  )
  </script>
  
  <style scoped>
  .chat-pdf-layout {
    height: 100vh;
    overflow: hidden;
  }
  </style>