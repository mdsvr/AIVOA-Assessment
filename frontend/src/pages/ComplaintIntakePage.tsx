import { AIIntakePanel } from '../features/aiIntake/AIIntakePanel'
import { ComplaintForm } from '../features/complaintForm/ComplaintForm'

export function ComplaintIntakePage() {
  return (
    <div className="intake-page">
      <ComplaintForm />
      <AIIntakePanel />
    </div>
  )
}
