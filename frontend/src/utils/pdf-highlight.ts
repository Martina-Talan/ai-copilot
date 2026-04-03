import type { Coordinates, SourceItem } from '../types/chat-types'

export const extractAnchor = (answer: string) => {
  const firstLine = (answer || '').split(/[\r\n]+/)[0] || ''
  const sentence = firstLine.split(/[.!?]/)[0] || firstLine
  return sentence.length >= 20 ? sentence : (answer || '')
}

export const norm = (s: string) =>
  s.normalize('NFKC').toLowerCase().replace(/\s+/g, ' ').trim()

export const scorePageForSnippet = async (
  pdfInstance: any,
  pageNumber: number,
  textSnippet: string
): Promise<{ coords: Coordinates | null; score: number }> => {
  if (!pdfInstance || !textSnippet?.trim()) return { coords: null, score: 0 }

  try {
    const page = await pdfInstance.getPage(pageNumber)
    const textContent = await page.getTextContent()
    const items = textContent.items as any[]

    const N = (s: string) => s.normalize('NFKC').toLowerCase().replace(/\s+/g, ' ').trim()
    const snip = N(textSnippet)

    const strongPatterns: RegExp[] = [
      /\b\d{1,2}\.\d{1,2}\.\d{4}\b/u,
      /\b\d{1,3}(?:\.\d{3})*,\d{2}\b/u,
      /\b\d+[.,]\d{2}\b/u
    ]

    const normItems = items.map(it => ({
      raw: String(it.str || ''),
      n: N(String(it.str || '')),
      y: Number(it.transform?.[5] ?? 0),
      h: Math.abs(Number(it.transform?.[3] ?? it.height ?? 10)) || 10,
      x: Number(it.transform?.[4] ?? 0),
      w: Number(it.width ?? Math.max(40, (String(it.str || '').length || 10) * 4.5)),
    }))

    const hasStrong = strongPatterns.some(rx => rx.test(snip))
    if (hasStrong) {
      let bestOne: any = null
      let bestScore = 0

      for (const ni of normItems) {
        let s = 0
        for (const rx of strongPatterns) {
          if (rx.test(ni.raw) || rx.test(ni.n)) s += 100
        }
        if (snip.includes(ni.n)) s += 10
        if (s > bestScore) {
          bestScore = s
          bestOne = ni
        }
      }

      if (bestOne && bestScore > 0) {
        return {
          coords: {
            x: bestOne.x,
            y: bestOne.y,
            width: bestOne.w,
            height: bestOne.h,
            page: pageNumber,
            fromPdfSpace: true,
          },
          score: bestScore,
        }
      }
    }

    const rawTokens = Array.from(new Set(
      snip.split(/[^0-9\p{L}]+/u).filter(t => t.length >= 3)
    ))

    const isNum = (t: string) => /^\d{4,}$/.test(t) || /\d/.test(t)
    const isBrandy = (t: string) => /(gmbh|ag|kg|mbh|d\.?o\.?o\.?)/i.test(t)

    const tokens = rawTokens
      .sort((a, b) => {
        const wa = (isNum(a) ? 3 : 0) + (isBrandy(a) ? 2 : 0)
        const wb = (isNum(b) ? 3 : 0) + (isBrandy(b) ? 2 : 0)
        return wb - wa
      })
      .map(t => N(t))

    let bestScore = 0
    let bestWindow: { start: number; end: number } | null = null
    const MAX_W = 10

    for (let i = 0; i < normItems.length; i++) {
      let acc = ''
      const matched = new Set<string>()

      for (let w = 1; w <= MAX_W && i + w <= normItems.length; w++) {
        const j = i + w - 1
        const baseY = normItems[i].y
        const avgH = (normItems[i].h + normItems[j].h) / 2
        const LINE_TOL = avgH * 1.5

        if (Math.abs(normItems[j].y - baseY) > LINE_TOL) break

        acc = (acc ? acc + ' ' : '') + normItems[j].n

        let s = 0
        for (const t of tokens) {
          if (!matched.has(t) && acc.includes(t)) {
            matched.add(t)
            s += 6
            if (isNum(t)) s += 6
            if (isBrandy(t)) s += 6
          }
        }

        if (s > bestScore) {
          bestScore = s
          bestWindow = { start: i, end: j }
        }
      }
    }

    if (!bestWindow || bestScore === 0) return { coords: null, score: 0 }

    const slice = normItems.slice(bestWindow.start, bestWindow.end + 1)
    const refY = slice[0].y
    const refH = slice.reduce((a, b) => a + b.h, 0) / slice.length
    const LINE_TOL = refH * 1.5
    const sameLine = slice.filter(it => Math.abs(it.y - refY) <= LINE_TOL)

    const left = Math.min(...sameLine.map(it => it.x))
    const right = Math.max(...sameLine.map(it => it.x + it.w))
    const bottom = Math.min(...sameLine.map(it => it.y))
    const top = Math.max(...sameLine.map(it => it.y + it.h))

    return {
      coords: {
        x: left,
        y: bottom,
        width: right - left,
        height: top - bottom,
        page: pageNumber,
        fromPdfSpace: true,
      },
      score: bestScore,
    }
  } catch (e) {
    console.warn('scorePageForSnippet failed:', e)
    return { coords: null, score: 0 }
  }
}

export const computeParagraphBoxes = async (
  pdfInstance: any,
  pageNumber: number,
  textSnippet: string
): Promise<Coordinates[] | null> => {
  if (!pdfInstance || !textSnippet?.trim()) return null

  const N = (s: string) => s.normalize('NFKC').toLowerCase().replace(/\s+/g, ' ').trim()
  const snip = N(textSnippet)

  const SNIP_TOKENS = Array.from(
    new Set(snip.split(/[^0-9\p{L}]+/u).filter(t => t.length >= 3))
  ).slice(0, 60)
  const SNIP_SET = new Set(SNIP_TOKENS)

  const strongRx = [
    /\b\d{1,2}\.\d{1,2}\.\d{4}\b/u,
    /\b\d{1,3}(?:\.\d{3})*,\d{2}\b/u,
    /\b\d+[.,]\d{2}\b/u
  ]
  const dateOnlyRx = /^\s*\d{1,2}\.\d{1,2}\.\d{4}\s*$/

  const page = await pdfInstance.getPage(pageNumber)
  const tc = await page.getTextContent()
  const items = (tc.items as any[]).map(i => {
    const x = Number(i.transform?.[4] ?? 0)
    const y = Number(i.transform?.[5] ?? 0)
    const h = Math.abs(Number(i.transform?.[3] ?? i.height ?? 10)) || 10
    const w = Number(i.width ?? Math.max(40, (String(i.str || '').length || 10) * 4.5))
    const raw = String(i.str || '')
    return { raw, n: N(raw), x, y, w, h }
  }).filter(i => i.raw)

  if (!items.length) return null

  const sorted = [...items].sort((a, b) => b.y - a.y)
  const lines: Array<{ items: typeof items; y: number; h: number; n: string; raw: string }> = []

  for (const t of sorted) {
    const last = lines[lines.length - 1]
    if (!last) {
      lines.push({ items: [t], y: t.y, h: t.h, n: t.n, raw: t.raw })
      continue
    }

    const tol = Math.max(last.h, t.h) * 0.7
    if (Math.abs(t.y - last.y) <= tol) {
      last.items.push(t)
      last.h = (last.h + t.h) / 2
      last.n = (last.n ? last.n + ' ' : '') + t.n
      last.raw = (last.raw ? last.raw + ' ' : '') + t.raw
    } else {
      lines.push({ items: [t], y: t.y, h: t.h, n: t.n, raw: t.raw })
    }
  }

  for (const L of lines) {
    L.items.sort((a, b) => a.x - b.x)
  }

  const lineScore = (L: typeof lines[number]) => {
    if (dateOnlyRx.test(L.raw)) return 0.01

    const toks = L.n.split(/[^0-9\p{L}]+/u).filter(t => t.length >= 3)
    const setL = new Set(toks)
    let inter = 0
    for (const t of setL) if (SNIP_SET.has(t)) inter++
    const union = new Set([...setL, ...SNIP_SET]).size || 1
    let score = inter / union

    if (L.raw.length < 12) score *= 0.35

    let strong = 0
    for (const rx of strongRx) {
      if (rx.test(L.raw) || rx.test(L.n)) strong++
    }
    score += strong * 0.03

    return score
  }

  const scores = lines.map(lineScore)
  const HARD_MIN = 0.22
  const SOFT_MIN = 0.14
  const MAX_LINES = 14
  const GAP_TOL = 2

  let seed = -1
  let seedScore = 0
  for (let i = 0; i < scores.length; i++) {
    if (scores[i] > HARD_MIN && scores[i] > seedScore) {
      seed = i
      seedScore = scores[i]
    }
  }

  if (seed === -1) return null

  let top = seed
  let bot = seed
  let badUp = 0
  let badDown = 0

  while (top > 0 && (bot - top + 1) < MAX_LINES) {
    if (scores[top - 1] >= SOFT_MIN) {
      top--
      badUp = 0
    } else if (++badUp > GAP_TOL) {
      break
    } else {
      top--
    }
  }

  while (bot < scores.length - 1 && (bot - top + 1) < MAX_LINES) {
    if (scores[bot + 1] >= SOFT_MIN) {
      bot++
      badDown = 0
    } else if (++badDown > GAP_TOL) {
      break
    } else {
      bot++
    }
  }

  while (top <= bot && scores[top] < SOFT_MIN) top++
  while (bot >= top && scores[bot] < SOFT_MIN) bot--

  if (bot < top) return null

  const blockText = lines.slice(top, bot + 1).map(L => L.n).join(' ')
  const blockTokens = new Set(blockText.split(/[^0-9\p{L}]+/u).filter(t => t.length >= 3))
  let matched = 0
  for (const t of blockTokens) if (SNIP_SET.has(t)) matched++
  if (matched < 5) return null

  const avgH = (() => {
    const all = lines.slice(top, bot + 1).flatMap(L => L.items.map(i => i.h))
    return all.reduce((a, b) => a + b, 0) / Math.max(all.length, 1)
  })()

  const MAX_TOTAL_H = avgH * 25
  let boxes: Coordinates[] = []
  let totalH = 0

  for (let i = top; i <= bot; i++) {
    const L = lines[i]
    const left = Math.min(...L.items.map(k => k.x))
    const right = Math.max(...L.items.map(k => k.x + k.w))
    const bottom = Math.min(...L.items.map(k => k.y))
    const topY = Math.max(...L.items.map(k => k.y + k.h))
    const h = topY - bottom

    if (totalH + h > MAX_TOTAL_H) break
    totalH += h

    boxes.push({
      x: left,
      y: bottom,
      width: right - left,
      height: h,
      page: pageNumber,
      fromPdfSpace: true,
    })
  }

  return boxes.length ? boxes : null
}

export const findParagraphBoxesAnyPage = async (
  pdfInstance: any,
  snippet: string,
  preferredPages: number[] = []
): Promise<Coordinates[] | null> => {
  if (!pdfInstance || !snippet?.trim()) return null

  for (const p of preferredPages) {
    const b = await computeParagraphBoxes(pdfInstance, p, snippet)
    if (b?.length) return b
  }

  const totalPages = pdfInstance?.numPages || 0
  for (let p = 1; p <= totalPages; p++) {
    if (preferredPages.includes(p)) continue
    const b = await computeParagraphBoxes(pdfInstance, p, snippet)
    if (b?.length) return b
  }

  return null
}

const MIN_ACCEPTABLE_SCORE = 18

export const findBestCoords = async (
  pdfInstance: any,
  finalAnswer: string,
  srcs: SourceItem[]
): Promise<Coordinates | null> => {
  const anchor = extractAnchor(finalAnswer)
  const numPages = pdfInstance?.numPages || 0
  if (!anchor || !numPages) return null

  const byConf = [...(srcs || [])]
    .filter(s => Number.isFinite(s.pageNumber))
    .sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0))

  const seen = new Set<number>()
  const candidates: number[] = []

  for (const s of byConf) {
    if (!seen.has(s.pageNumber)) {
      candidates.push(s.pageNumber)
      seen.add(s.pageNumber)
    }
  }

  for (let p = 1; p <= numPages; p++) {
    if (!seen.has(p)) candidates.push(p)
  }

  let best: { coords: Coordinates | null; score: number } = { coords: null, score: 0 }

  for (const p of candidates) {
    const r = await scorePageForSnippet(pdfInstance, p, anchor)
    if (r.score > best.score) best = r
    if (r.score >= MIN_ACCEPTABLE_SCORE) return r.coords
  }

  return best.coords
}