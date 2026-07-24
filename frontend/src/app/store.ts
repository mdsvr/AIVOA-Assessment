import { configureStore } from '@reduxjs/toolkit'
import { complaintsApi } from '../api/complaintsApi'
import complaintFormReducer from '../features/complaintForm/complaintFormSlice'
import extractionReducer from '../features/aiIntake/extractionSlice'

export const store = configureStore({
  reducer: {
    complaintForm: complaintFormReducer,
    extraction: extractionReducer,
    [complaintsApi.reducerPath]: complaintsApi.reducer,
  },
  middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(complaintsApi.middleware),
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
