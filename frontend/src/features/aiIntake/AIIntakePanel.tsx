import { useState } from 'react'
import { extractComplaint, type ExtractionResult } from '../../api/streaming'
import { useAppDispatch, useAppSelector } from '../../app/hooks'
import { applyExtractionResult } from '../complaintForm/complaintFormSlice'
import { ChatBox } from './ChatBox'
import { Dropzone } from './Dropzone'
import { EXTRACTION_NODES, extractFailed, extractProgress, extractStarted, extractSucceeded } from './extractionSlice'

export function AIIntakePanel() {
  const dispatch = useAppDispatch()
  const { status, completedNodes, errorMessage } = useAppSelector((s) => s.extraction)
  const [pasteMode, setPasteMode] = useState(false)
  const [pastedText, setPastedText] = useState('')

  const runExtraction = async (input: { file?: File; pastedText?: string }) => {
    dispatch(extractStarted())
    await extractComplaint(input, (event, data) => {
      if (event === 'progress') {
        dispatch(extractProgress((data as { node: string }).node))
      } else if (event === 'result') {
        const result = data as ExtractionResult
        dispatch(
          applyExtractionResult({
            fields: result.fields,
            completeness_score: result.completeness_score,
            risk_classification: result.risk_classification,
            ai_summary: result.ai_summary,
            duplicates: result.duplicates,
            duplicates_error: result.duplicates_error,
            source_text: result.source_text,
            source_filename: result.source_filename,
          }),
        )
        dispatch(extractSucceeded())
      } else if (event === 'error') {
        dispatch(extractFailed((data as { message: string }).message))
      }
    })
  }

  const progressPct =
    status === 'extracting' ? Math.round((completedNodes.length / EXTRACTION_NODES.length) * 100) : 0
  const currentLabel =
    EXTRACTION_NODES.find((n) => !completedNodes.includes(n.key))?.label ??
    'Finishing up...'

  return (
    <section className="panel">
      <header className="panel-header">
        <div className="ai-title">
          <span className="ai-sparkle">✦</span>
          <h2>AI Complaint Intake Assistant</h2>
        </div>
        <span className="beta-badge">BETA</span>
      </header>

      {!pasteMode && <Dropzone onFileSelected={(file) => runExtraction({ file })} />}
      {pasteMode && (
        <div className="paste-area">
          <textarea
            rows={6}
            placeholder="Paste complaint text or email content here..."
            value={pastedText}
            onChange={(e) => setPastedText(e.target.value)}
          />
          <button
            type="button"
            className="btn btn-primary"
            disabled={!pastedText.trim()}
            onClick={() => runExtraction({ pastedText })}
          >
            Extract from Text
          </button>
        </div>
      )}

      <div className="paste-toggle-row">
        <hr />
        <span>OR</span>
        <hr />
      </div>
      <button type="button" className="btn btn-secondary btn-block" onClick={() => setPasteMode((v) => !v)}>
        {pasteMode ? 'Upload a File Instead' : 'Paste Complaint Text / Email'}
      </button>

      <p className="upload-hint">Supported formats: PDF, DOCX, TXT, EML. Max file size: 10MB.</p>

      {status === 'extracting' && (
        <div className="extraction-progress">
          <h3>Extraction Progress</h3>
          <div className="progress-bar">
            <div className="progress-bar-fill" style={{ width: `${progressPct}%` }} />
          </div>
          <p>{currentLabel}</p>
        </div>
      )}
      {status === 'error' && <p className="error-text">{errorMessage}</p>}

      <h3 className="assistant-heading">AI Assistant</h3>
      <ChatBox />
    </section>
  )
}
