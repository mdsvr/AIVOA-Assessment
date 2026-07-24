import { useState } from 'react'
import { useAppDispatch, useAppSelector } from '../../app/hooks'
import { useSaveComplaintMutation } from '../../api/complaintsApi'
import { Badge } from '../../components/Badge'
import { FormField } from '../../components/FormField'
import { resetExtraction } from '../aiIntake/extractionSlice'
import { emptyFields, resetForm, setField, type ComplaintFields } from './complaintFormSlice'

const PLACEHOLDER = 'Awaiting AI extraction...'

function TextInput({ name }: { name: keyof ComplaintFields }) {
  const value = useAppSelector((s) => s.complaintForm.fields[name])
  const dispatch = useAppDispatch()
  return (
    <input
      type="text"
      value={value ?? ''}
      placeholder={PLACEHOLDER}
      onChange={(e) => dispatch(setField({ key: name, value: e.target.value || null }))}
    />
  )
}

function DateInput({ name }: { name: keyof ComplaintFields }) {
  const value = useAppSelector((s) => s.complaintForm.fields[name])
  const dispatch = useAppDispatch()
  return (
    <input
      type="date"
      value={value ?? ''}
      onChange={(e) => dispatch(setField({ key: name, value: e.target.value || null }))}
    />
  )
}

function NumberInput({ name }: { name: keyof ComplaintFields }) {
  const value = useAppSelector((s) => s.complaintForm.fields[name])
  const dispatch = useAppDispatch()
  return (
    <input
      type="number"
      value={value ?? ''}
      placeholder={PLACEHOLDER}
      onChange={(e) =>
        dispatch(setField({ key: name, value: e.target.value === '' ? null : Number(e.target.value) }))
      }
    />
  )
}

function TextArea({ name }: { name: keyof ComplaintFields }) {
  const value = useAppSelector((s) => s.complaintForm.fields[name])
  const dispatch = useAppDispatch()
  return (
    <textarea
      value={value ?? ''}
      placeholder={PLACEHOLDER}
      rows={4}
      onChange={(e) => dispatch(setField({ key: name, value: e.target.value || null }))}
    />
  )
}

function SelectInput({
  name,
  options,
}: {
  name: keyof ComplaintFields
  options: string[]
}) {
  const value = useAppSelector((s) => s.complaintForm.fields[name])
  const dispatch = useAppDispatch()
  return (
    <select value={value ?? ''} onChange={(e) => dispatch(setField({ key: name, value: e.target.value || null }))}>
      <option value="">{PLACEHOLDER}</option>
      {options.map((o) => (
        <option key={o} value={o}>
          {o[0].toUpperCase() + o.slice(1)}
        </option>
      ))}
    </select>
  )
}

export function ComplaintForm() {
  const dispatch = useAppDispatch()
  const state = useAppSelector((s) => s.complaintForm)
  const [saveComplaint, { isLoading, isSuccess }] = useSaveComplaintMutation()
  const [saveError, setSaveError] = useState<string | null>(null)

  const handleReset = () => {
    dispatch(resetForm())
    dispatch(resetExtraction())
    setSaveError(null)
  }

  const handleSave = async () => {
    setSaveError(null)
    try {
      await saveComplaint({
        ...state.fields,
        source_text: state.sourceText,
        source_filename: state.sourceFilename,
        completeness_score: state.completenessScore,
        risk_classification: state.riskClassification,
        ai_summary: state.aiSummary,
      }).unwrap()
      dispatch(resetForm())
      dispatch(resetExtraction())
    } catch {
      setSaveError('Could not save complaint. Check the backend is running and try again.')
    }
  }

  const isEmpty = JSON.stringify(state.fields) === JSON.stringify(emptyFields)

  return (
    <section className="panel">
      <header className="panel-header">
        <div>
          <h1>Log Customer Complaint</h1>
          <p className="subtitle">API &amp; FDF Quality Assurance Module</p>
        </div>
        <Badge tone="pending">Pending Triage</Badge>
      </header>

      {state.completenessScore !== null && (
        <div className="ai-insight-row">
          <span>Completeness: {Math.round(state.completenessScore * 100)}%</span>
          {state.riskClassification && <span>Risk: {state.riskClassification}</span>}
        </div>
      )}
      {state.aiSummary && <p className="ai-summary">{state.aiSummary}</p>}
      {state.duplicates.length > 0 && (
        <div className="duplicate-warning">
          Possible duplicate of complaint #{state.duplicates[0].complaint_id} (
          {Math.round(state.duplicates[0].similarity * 100)}% similar)
        </div>
      )}

      <fieldset>
        <legend>1. Origin &amp; Customer Details</legend>
        <div className="field-grid">
          <FormField label="Complaint Source">
            <TextInput name="complaint_source" />
          </FormField>
          <FormField label="Customer Name">
            <TextInput name="customer_name" />
          </FormField>
        </div>
      </fieldset>

      <fieldset>
        <legend>2. Product &amp; Batch Identification</legend>
        <div className="field-grid">
          <FormField label="Product Name">
            <TextInput name="product_name" />
          </FormField>
          <FormField label="Product Strength/Grade">
            <TextInput name="product_strength" />
          </FormField>
          <FormField label="Batch/Lot Number">
            <TextInput name="batch_lot_number" />
          </FormField>
          <FormField label="Manufacturing Date">
            <DateInput name="manufacturing_date" />
          </FormField>
          <FormField label="Expiry Date">
            <DateInput name="expiry_date" />
          </FormField>
          <FormField label="Quantity Affected" suffix={state.fields.quantity_unit ?? 'kg'}>
            <NumberInput name="quantity_affected" />
          </FormField>
        </div>
      </fieldset>

      <fieldset>
        <legend>3. Complaint Details</legend>
        <div className="field-grid">
          <FormField label="Complaint Type">
            <TextInput name="complaint_type" />
          </FormField>
          <FormField label="Complaint Date">
            <DateInput name="complaint_date" />
          </FormField>
        </div>
        <FormField label="Detailed Complaint Description">
          <TextArea name="description" />
        </FormField>
      </fieldset>

      <fieldset>
        <legend>4. Initial Assessment &amp; Priority</legend>
        <div className="field-grid">
          <FormField label="Initial Severity">
            <SelectInput name="initial_severity" options={['critical', 'major', 'minor']} />
          </FormField>
          <FormField label="Priority">
            <SelectInput name="priority" options={['high', 'medium', 'low']} />
          </FormField>
        </div>
      </fieldset>

      <footer className="panel-footer">
        <button type="button" className="btn btn-secondary" onClick={handleReset}>
          Reset Form
        </button>
        <div className="save-area">
          {saveError && <span className="error-text">{saveError}</span>}
          {isSuccess && <span className="success-text">Saved.</span>}
          <button
            type="button"
            className="btn btn-primary"
            disabled={isEmpty || isLoading}
            onClick={handleSave}
          >
            {isLoading ? 'Saving...' : 'Save Complaint'}
          </button>
        </div>
      </footer>
    </section>
  )
}
