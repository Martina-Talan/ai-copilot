export type Coordinates = {
    x: number
    y: number
    width?: number
    height?: number
    page: number
    viewportScale?: number
    fromPdfSpace?: boolean
    confidence?: number
    matchedText?: string
  }
  
  export type SourceItem = {
    filename?: string
    pageNumber: number
    textMatch?: string
    confidence: number
    coordinates?: Coordinates | null
  }
  
  export type ChatAnswer = {
    contextAnswer?: string
    additionalInfo?: string
  } | null