import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

export interface ComplaintFields {
  complaint_source: string | null
  customer_name: string | null
  product_name: string | null
  product_strength: string | null
  batch_lot_number: string | null
  manufacturing_date: string | null
  expiry_date: string | null
  quantity_affected: number | null
  quantity_unit: string | null
  complaint_type: string | null
  complaint_date: string | null
  description: string | null
  initial_severity: string | null
  priority: string | null
}

export const emptyFields: ComplaintFields = {
  complaint_source: null,
  customer_name: null,
  product_name: null,
  product_strength: null,
  batch_lot_number: null,
  manufacturing_date: null,
  expiry_date: null,
  quantity_affected: null,
  quantity_unit: null,
  complaint_type: null,
  complaint_date: null,
  description: null,
  initial_severity: null,
  priority: null,
}

interface ComplaintFormState {
  fields: ComplaintFields
  sourceText: string | null
  sourceFilename: string | null
  completenessScore: number | null
  riskClassification: string | null
  aiSummary: string | null
  duplicates: Array<{
    complaint_id: number
    similarity: number
    product_name: string | null
    customer_name: string | null
  }>
}

const initialState: ComplaintFormState = {
  fields: emptyFields,
  sourceText: null,
  sourceFilename: null,
  completenessScore: null,
  riskClassification: null,
  aiSummary: null,
  duplicates: [],
}

const complaintFormSlice = createSlice({
  name: 'complaintForm',
  initialState,
  reducers: {
    setField(
      state,
      action: PayloadAction<{ key: keyof ComplaintFields; value: string | number | null }>,
    ) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ;(state.fields as any)[action.payload.key] = action.payload.value
    },
    applyExtractionResult(
      state,
      action: PayloadAction<{
        fields: Partial<ComplaintFields>
        completeness_score: number
        risk_classification: string | null
        ai_summary: string | null
        duplicates: ComplaintFormState['duplicates']
        source_text: string
        source_filename: string
      }>,
    ) {
      state.fields = { ...state.fields, ...action.payload.fields }
      state.completenessScore = action.payload.completeness_score
      state.riskClassification = action.payload.risk_classification
      state.aiSummary = action.payload.ai_summary
      state.duplicates = action.payload.duplicates
      state.sourceText = action.payload.source_text
      state.sourceFilename = action.payload.source_filename
    },
    resetForm() {
      return initialState
    },
  },
})

export const { setField, applyExtractionResult, resetForm } = complaintFormSlice.actions
export default complaintFormSlice.reducer
