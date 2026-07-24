import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'
import type { ComplaintFields } from '../features/complaintForm/complaintFormSlice'

export interface ComplaintOut extends ComplaintFields {
  id: number
  status: string
  completeness_score: number | null
  risk_classification: string | null
  ai_summary: string | null
  created_at: string
  updated_at: string
}

export interface ComplaintCreate extends ComplaintFields {
  source_text?: string | null
  source_filename?: string | null
  completeness_score?: number | null
  risk_classification?: string | null
  ai_summary?: string | null
  raw_extraction?: Record<string, unknown> | null
}

export const complaintsApi = createApi({
  reducerPath: 'complaintsApi',
  baseQuery: fetchBaseQuery({ baseUrl: '/api/complaints' }),
  tagTypes: ['Complaint'],
  endpoints: (builder) => ({
    listComplaints: builder.query<ComplaintOut[], void>({
      query: () => '',
      providesTags: ['Complaint'],
    }),
    getComplaint: builder.query<ComplaintOut, number>({
      query: (id) => `/${id}`,
      providesTags: ['Complaint'],
    }),
    saveComplaint: builder.mutation<ComplaintOut, ComplaintCreate>({
      query: (body) => ({ url: '', method: 'POST', body }),
      invalidatesTags: ['Complaint'],
    }),
  }),
})

export const { useListComplaintsQuery, useGetComplaintQuery, useSaveComplaintMutation } =
  complaintsApi
