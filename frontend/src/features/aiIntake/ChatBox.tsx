import { useState } from 'react'
import { chatWithComplaint } from '../../api/streaming'
import { useAppDispatch, useAppSelector } from '../../app/hooks'
import { chatFailed, chatStreamEnded, chatTokenAppended, chatUserMessageSent } from './extractionSlice'

export function ChatBox() {
  const dispatch = useAppDispatch()
  const { chatMessages, chatStreaming, chatError } = useAppSelector((s) => s.extraction)
  const { fields, sourceText, aiSummary } = useAppSelector((s) => s.complaintForm)
  const [draft, setDraft] = useState('')

  const send = async () => {
    const message = draft.trim()
    if (!message || chatStreaming) return
    setDraft('')

    // Exclude the placeholder assistant bubble chatUserMessageSent is about to add, and
    // any empty-content message left behind by a previously failed turn -- resending
    // that as history would feed the LLM a blank assistant message.
    const history = chatMessages
      .filter((m) => m.content)
      .map((m) => ({ role: m.role, content: m.content }))
    dispatch(chatUserMessageSent(message))

    await chatWithComplaint(
      { message, context: fields, source_text: sourceText, ai_summary: aiSummary, history },
      (event, data) => {
        if (event === 'token') {
          dispatch(chatTokenAppended((data as { token: string }).token))
        } else if (event === 'done') {
          dispatch(chatStreamEnded())
        } else if (event === 'error') {
          const message = (data as { message?: string } | null | undefined)?.message
          dispatch(chatFailed(message ?? 'Something went wrong.'))
        }
      },
    ).catch(() => dispatch(chatFailed('Chat request failed. Check the backend is running.')))
  }

  return (
    <div className="chatbox">
      <div className="chatbox-messages">
        {chatMessages.length === 0 && (
          <div className="ai-assistant-bubble">
            Upload a complaint document or paste text above. I will automatically extract
            the details and populate the form for you.
          </div>
        )}
        {chatMessages.map((m, i) => (
          <div key={i} className={`chat-message chat-message-${m.role}`}>
            {m.content || (chatStreaming && i === chatMessages.length - 1 ? '...' : '')}
          </div>
        ))}
      </div>
      {chatError && (
        <p className="error-text" role="alert">
          {chatError}
        </p>
      )}
      <div className="chatbox-input">
        <input
          type="text"
          placeholder="Ask me anything about this complaint..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') send()
          }}
        />
        <button type="button" onClick={send} disabled={chatStreaming || !draft.trim()}>
          Send
        </button>
      </div>
      <p className="chatbox-disclaimer">AI responses may contain errors. Please verify information.</p>
    </div>
  )
}
