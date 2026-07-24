import type { ComplaintFields } from '../features/complaintForm/complaintFormSlice'

// The browser's EventSource API only supports GET requests with no body, so it can't
// carry an uploaded file or a chat message. Both streaming endpoints are POST + SSE,
// consumed here via fetch() + a ReadableStream reader instead.

export interface DuplicateMatch {
  complaint_id: number
  similarity: number
  product_name: string | null
  customer_name: string | null
}

export interface ExtractionResult {
  fields: Partial<ComplaintFields>
  completeness_score: number
  risk_classification: string | null
  ai_summary: string | null
  duplicates: DuplicateMatch[]
  duplicates_error: string | null
  source_text: string
  source_filename: string
}

async function* parseSSEStream(response: Response): AsyncGenerator<{ event: string; data: unknown }> {
  const reader = response.body?.getReader()
  if (!reader) return
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let sepIndex: number
    while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
      const rawEvent = buffer.slice(0, sepIndex)
      buffer = buffer.slice(sepIndex + 2)

      let event = 'message'
      let dataLine = ''
      for (const line of rawEvent.split('\n')) {
        if (line.startsWith('event: ')) event = line.slice(7)
        else if (line.startsWith('data: ')) dataLine = line.slice(6)
      }
      if (dataLine) yield { event, data: JSON.parse(dataLine) }
    }
  }
}

export async function extractComplaint(
  input: { file?: File; pastedText?: string },
  onEvent: (event: 'progress' | 'result' | 'error', data: unknown) => void,
): Promise<void> {
  const form = new FormData()
  if (input.file) form.append('file', input.file)
  if (input.pastedText) form.append('pasted_text', input.pastedText)

  const response = await fetch('/api/complaints/extract', { method: 'POST', body: form })
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }))
    onEvent('error', { message: body.detail ?? 'Extraction failed' })
    return
  }
  for await (const { event, data } of parseSSEStream(response)) {
    onEvent(event as 'progress' | 'result' | 'error', data)
  }
}

export interface ChatTurnRequest {
  message: string
  context: Partial<ComplaintFields>
  source_text?: string | null
  ai_summary?: string | null
  history: Array<{ role: 'user' | 'assistant'; content: string }>
}

// Stateless: the complaint being chatted about may not be saved yet (the reference UI
// shows the assistant active during intake, before Save), so the current form context
// and conversation history are sent with every turn instead of looked up by an id.
export async function chatWithComplaint(
  payload: ChatTurnRequest,
  onEvent: (event: 'token' | 'done' | 'error', data: unknown) => void,
): Promise<void> {
  const response = await fetch('/api/complaints/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    onEvent('error', { message: 'Chat request failed' })
    return
  }
  for await (const { event, data } of parseSSEStream(response)) {
    onEvent(event as 'token' | 'done' | 'error', data)
  }
}
