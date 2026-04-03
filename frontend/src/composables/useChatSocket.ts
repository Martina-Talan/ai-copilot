import { ref, nextTick } from 'vue'
import type { ChatAnswer, Coordinates, SourceItem } from '../types/chat-types'
import {
  findParagraphBoxesAnyPage,
  findBestCoords,
} from '../utils/pdf-highlight'

const WS_URL = 'ws://localhost:8001/ws'

export function useChatSocket(options: {
  documentId: string
  renderPage: (pageNumber: number, highlight?: Coordinates | Coordinates[] | null) => Promise<void>
  clearAllHighlights: () => Promise<void>
  scrollToPage: (page: number) => void
  getPdfInstance: () => any
  addAssistantMessage: (content: string, sources?: { pageNumber: number }[]) => void
  scrollToBottom: () => void
}) {
  const answer = ref<ChatAnswer>({ contextAnswer: '', additionalInfo: '' })
  const sources = ref<SourceItem[]>([])
  const error = ref('')
  const loading = ref(false)
  const isStreaming = ref(false)

  const anchorPhrases = ref<string[]>([])
  const primaryHighlight = ref<Coordinates | null>(null)
  const fullAnswer = ref('')

  let socket: WebSocket | null = null
  let streamedAnswer = ''
  let currentReqId = 0

  const resetAskState = () => {
    sources.value = []
    streamedAnswer = ''
    fullAnswer.value = ''
    anchorPhrases.value = []
    primaryHighlight.value = null
    answer.value = { contextAnswer: '', additionalInfo: '' }
    error.value = ''
    loading.value = true
    isStreaming.value = true
  }

  const parseSources = (rawSources: any[]): SourceItem[] => {
    return (rawSources || [])
      .map((source): SourceItem => ({
        filename: source.filename,
        pageNumber: source.pageNumber ?? source.page ?? 1,
        textMatch: source.textMatch,
        confidence: source.confidence ?? 0,
        coordinates: source.coordinates
          ? {
              x: source.coordinates.x,
              y: source.coordinates.y,
              width: source.coordinates.width,
              height: source.coordinates.height,
              page: source.coordinates.page ?? (source.pageNumber ?? 1),
              fromPdfSpace: source.coordinates.fromPdfSpace ?? true,
              viewportScale: source.coordinates.viewportScale,
              confidence: source.coordinates.confidence,
              matchedText: source.coordinates.matchedText,
            }
          : null,
      }))
      .sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0))
  }

  const handleSourcesMessage = async (data: any) => {
    sources.value = parseSources(data.sources || [])

    const firstSourceWithCoords = sources.value.find(source => source.coordinates)
    if (firstSourceWithCoords?.coordinates) {
      await options.renderPage(
        firstSourceWithCoords.coordinates.page,
        firstSourceWithCoords.coordinates
      )
      options.scrollToPage(firstSourceWithCoords.coordinates.page)
    }
  }

  const handleAnswerMessage = async (data: any) => {
    if (!answer.value) {
      answer.value = { contextAnswer: '', additionalInfo: '' }
    }

    streamedAnswer += data.token
    answer.value.contextAnswer = streamedAnswer

    await nextTick()
    options.scrollToBottom()
  }

  const handleSourceReferencesMessage = (data: any) => {
    try {
      fullAnswer.value = data.fullAnswer || fullAnswer.value
      anchorPhrases.value = Array.isArray(data.anchorPhrases) ? data.anchorPhrases : []
      primaryHighlight.value = data.primaryHighlight
        ? {
            x: data.primaryHighlight.x,
            y: data.primaryHighlight.y,
            width: data.primaryHighlight.width,
            height: data.primaryHighlight.height,
            page: data.primaryHighlight.page,
            fromPdfSpace: true,
          }
        : null
    } catch (err) {
      console.warn('Failed parsing source_references:', err)
    }
  }

  const resolveFinalHighlight = async (finalText: string) => {
    const pdfInstance = options.getPdfInstance()

    if (!pdfInstance || !finalText.trim()) {
      return {
        chosen: null as Coordinates | null,
        paraBoxes: null as Coordinates[] | null,
      }
    }

    let chosen: Coordinates | null = null
    let paraBoxes: Coordinates[] | null = null

    const isLongAnswer = finalText.length > 180 || /[.!?]\s+\p{L}/u.test(finalText)

    if (isLongAnswer) {
      const preferredPages = [...sources.value]
        .sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0))
        .map(source => source.pageNumber)

      paraBoxes = await findParagraphBoxesAnyPage(pdfInstance, finalText, preferredPages)
    }

    if (!paraBoxes?.length) {
      const sourceWithCoordinates = sources.value.find(source => source.coordinates)
      if (sourceWithCoordinates?.coordinates) {
        chosen = sourceWithCoordinates.coordinates
      }

      if (!chosen && anchorPhrases.value.length) {
        for (const phrase of anchorPhrases.value) {
          const result = await findBestCoords(pdfInstance, phrase, sources.value)
          if (result) {
            chosen = result
            break
          }
        }
      }

      if (!chosen && finalText) {
        chosen = await findBestCoords(pdfInstance, finalText, sources.value)
      }

      if (!chosen && sources.value[0]?.textMatch) {
        chosen = await findBestCoords(
          pdfInstance,
          sources.value[0].textMatch!,
          sources.value
        )
      }

      if (!chosen && primaryHighlight.value) {
        chosen = primaryHighlight.value
      }
    }

    return { chosen, paraBoxes }
  }

  const handleDoneMessage = async () => {
    const finalText = (streamedAnswer || fullAnswer.value || '').trim()

    await options.clearAllHighlights()

    const { chosen, paraBoxes } = await resolveFinalHighlight(finalText)

    if (paraBoxes?.length) {
      await options.renderPage(paraBoxes[0].page, paraBoxes)
      options.scrollToPage(paraBoxes[0].page)
    } else if (chosen) {
      await options.renderPage(chosen.page, chosen)
      options.scrollToPage(chosen.page)
    }

    const pageForChat =
      paraBoxes?.[0]?.page ??
      chosen?.page ??
      sources.value[0]?.pageNumber ??
      null

    const sourcesForChat = pageForChat ? [{ pageNumber: pageForChat }] : []

    options.addAssistantMessage(finalText, sourcesForChat)

    loading.value = false
    isStreaming.value = false
    answer.value = null
    streamedAnswer = ''

    await nextTick()
    options.scrollToBottom()
  }

  const handleErrorMessage = (data: any) => {
    error.value = data.message || 'Something went wrong.'
    loading.value = false
    isStreaming.value = false
  }

  const connectWebSocket = () => {
    try {
      socket?.close(1000)
    } catch {}

    socket = new WebSocket(WS_URL)

    socket.onopen = () => {
      console.log('WebSocket connected')
    }

    socket.onerror = (err) => {
      console.error('WebSocket error:', err)
      error.value = 'WebSocket connection failed'
      loading.value = false
      isStreaming.value = false
    }

    socket.onmessage = async (event) => {
      const data = JSON.parse(event.data)

      if (data.reqId != null && data.reqId !== currentReqId) {
        return
      }

      switch (data.type) {
        case 'sources':
          await handleSourcesMessage(data)
          break
        case 'answer':
          await handleAnswerMessage(data)
          break
        case 'source_references':
          handleSourceReferencesMessage(data)
          break
        case 'done':
          await handleDoneMessage()
          break
        case 'error':
          handleErrorMessage(data)
          break
      }
    }
  }

  const disconnectWebSocket = () => {
    try {
      socket?.close(1000, 'component unmounted')
    } catch {}
  }

  const sendQuestion = async (question: string) => {
    if (!question.trim() || !options.documentId) return

    resetAskState()
    await options.clearAllHighlights()

    const reqId = ++currentReqId
    const payload = {
      question,
      documentId: options.documentId,
      reqId,
    }

    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(payload))
      return
    }

    connectWebSocket()

    setTimeout(() => {
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(payload))
      } else {
        error.value = 'WebSocket not ready.'
        loading.value = false
        isStreaming.value = false
      }
    }, 150)
  }

  return {
    answer,
    sources,
    error,
    loading,
    isStreaming,
    connectWebSocket,
    disconnectWebSocket,
    sendQuestion,
  }
}