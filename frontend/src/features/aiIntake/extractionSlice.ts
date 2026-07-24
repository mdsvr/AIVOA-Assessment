import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

export const EXTRACTION_NODES = [
  { key: 'load_document', label: 'Reading document...' },
  { key: 'extract_fields', label: 'Extracting complaint details...' },
  { key: 'check_completeness', label: 'Checking completeness...' },
  { key: 'classify_risk', label: 'Assessing risk & priority...' },
  { key: 'detect_duplicates', label: 'Checking for duplicate complaints...' },
  { key: 'summarize', label: 'Summarizing complaint...' },
]

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

interface AiIntakeState {
  status: 'idle' | 'extracting' | 'done' | 'error'
  completedNodes: string[]
  errorMessage: string | null
  chatMessages: ChatMessage[]
  chatStreaming: boolean
  chatError: string | null
}

const initialState: AiIntakeState = {
  status: 'idle',
  completedNodes: [],
  errorMessage: null,
  chatMessages: [],
  chatStreaming: false,
  chatError: null,
}

const extractionSlice = createSlice({
  name: 'extraction',
  initialState,
  reducers: {
    extractStarted(state) {
      state.status = 'extracting'
      state.completedNodes = []
      state.errorMessage = null
    },
    extractProgress(state, action: PayloadAction<string>) {
      state.completedNodes.push(action.payload)
    },
    extractSucceeded(state) {
      state.status = 'done'
    },
    extractFailed(state, action: PayloadAction<string>) {
      state.status = 'error'
      state.errorMessage = action.payload
    },
    resetExtraction() {
      return initialState
    },
    chatUserMessageSent(state, action: PayloadAction<string>) {
      state.chatMessages.push({ role: 'user', content: action.payload })
      state.chatMessages.push({ role: 'assistant', content: '' })
      state.chatStreaming = true
      state.chatError = null
    },
    chatTokenAppended(state, action: PayloadAction<string>) {
      const last = state.chatMessages[state.chatMessages.length - 1]
      if (last && last.role === 'assistant') last.content += action.payload
    },
    chatStreamEnded(state) {
      state.chatStreaming = false
    },
    chatFailed(state, action: PayloadAction<string>) {
      state.chatStreaming = false
      state.chatError = action.payload
      // Drop both the empty placeholder and the question that triggered it -- leaving
      // either behind orphans an unanswered question in the transcript, and the empty
      // assistant message would otherwise get resent as blank-content history on the
      // next turn. Only applies when no tokens arrived before the failure; a reply that
      // fails partway through keeps whatever content it streamed.
      const last = state.chatMessages[state.chatMessages.length - 1]
      if (last && last.role === 'assistant' && !last.content) {
        state.chatMessages.pop()
        const prev = state.chatMessages[state.chatMessages.length - 1]
        if (prev && prev.role === 'user') state.chatMessages.pop()
      }
    },
  },
})

export const {
  extractStarted,
  extractProgress,
  extractSucceeded,
  extractFailed,
  resetExtraction,
  chatUserMessageSent,
  chatTokenAppended,
  chatStreamEnded,
  chatFailed,
} = extractionSlice.actions
export default extractionSlice.reducer
