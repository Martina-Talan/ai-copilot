import { ref, shallowRef, nextTick, type Ref, markRaw } from 'vue'
import { pdfjsLib } from '../pdf-worker'
import type { Coordinates } from '../types/chat-types'

const PDF_FETCH_BASE = 'http://localhost:3001/'
const FRONTEND_SCALE = 1.5

const HILITE_FILL = 'rgba(179,137,110,0.22)'
const HILITE_STROKE = 'rgba(179,137,110,0.95)'
const HILITE_LINE = 1.5
const HILITE_PAD_Y = 0

export function usePdfViewer() {
  const pdfPages = ref<number[]>([])
  const canvasRefs: Ref<(HTMLCanvasElement | null)[]> = ref([])
  const pdfInstance = shallowRef<any>(null)

  const setCanvasRef = (el: unknown, index: number) => {
    const element = (el as { $el?: unknown })?.$el ?? el
    if (element instanceof HTMLCanvasElement && index < canvasRefs.value.length) {
      canvasRefs.value[index] = element
    }
  }

  const scrollToPage = (page: number) => {
    canvasRefs.value[page - 1]?.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
    })
  }

  const renderPage = async (
    pageNumber: number,
    highlight?: Coordinates | Coordinates[] | null
  ) => {
    try {
      const page = await pdfInstance.value.getPage(pageNumber)
      const viewport = page.getViewport({ scale: FRONTEND_SCALE })

      const canvas = canvasRefs.value[pageNumber - 1]
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      if (!ctx) return

      const dpi = window.devicePixelRatio || 1
      canvas.width = Math.floor(viewport.width * dpi)
      canvas.height = Math.floor(viewport.height * dpi)
      canvas.style.width = `${viewport.width}px`
      canvas.style.height = `${viewport.height}px`
      ctx.setTransform(dpi, 0, 0, dpi, 0, 0)

      await page.render({ canvasContext: ctx, viewport }).promise

      if (!highlight) return
      const boxes = Array.isArray(highlight) ? highlight : [highlight]

      const drawBox = (box: Coordinates) => {
        if (!box) return

        if (box.fromPdfSpace) {
          const x2 = box.x + (box.width ?? 0)
          const y2 = box.y + (box.height ?? 0)
          const [vx1, vy1, vx2, vy2] = viewport.convertToViewportRectangle([box.x, box.y, x2, y2])

          const rx = Math.min(vx1, vx2)
          const ry = Math.min(vy1, vy2) - HILITE_PAD_Y
          const rw = Math.abs(vx2 - vx1)
          const rh = Math.abs(vy2 - vy1) + HILITE_PAD_Y * 2

          ctx.fillStyle = HILITE_FILL
          ctx.fillRect(rx, ry, rw, rh)
          ctx.strokeStyle = HILITE_STROKE
          ctx.lineWidth = HILITE_LINE
          ctx.strokeRect(rx, ry, rw, rh)
        } else {
          const scaleRatio = FRONTEND_SCALE / (box.viewportScale || FRONTEND_SCALE)
          const w = Math.max(1, (box.width || 1) * scaleRatio)
          const h = Math.max(1, (box.height || 1) * scaleRatio)
          const x = box.x * scaleRatio
          const y = box.y * scaleRatio

          ctx.fillStyle = HILITE_FILL
          ctx.fillRect(x, y, w, h)
          ctx.strokeStyle = HILITE_STROKE
          ctx.lineWidth = HILITE_LINE
          ctx.strokeRect(x, y, w, h)
        }
      }

      for (const b of boxes) drawBox(b)
    } catch (err) {
      console.error(`Error rendering page ${pageNumber}:`, err)
    }
  }

  const clearAllHighlights = async () => {
    await Promise.all(pdfPages.value.map(page => renderPage(page)))
  }

  const loadPdf = async (path: string) => {
    try {
      const data = await fetch(`${PDF_FETCH_BASE}${path}`).then(r => r.arrayBuffer())
      pdfInstance.value = markRaw(await pdfjsLib.getDocument({ data }).promise)

      const numPages = pdfInstance.value.numPages
      pdfPages.value = Array.from({ length: numPages }, (_, i) => i + 1)
      canvasRefs.value = Array(numPages).fill(null)

      await nextTick()
      await Promise.all(pdfPages.value.map(pageNum => renderPage(pageNum)))
    } catch (err) {
      console.error('Failed to load PDF:', err)
    }
  }

  return {
    pdfPages,
    canvasRefs,
    pdfInstance,
    setCanvasRef,
    renderPage,
    clearAllHighlights,
    scrollToPage,
    loadPdf,
  }
}