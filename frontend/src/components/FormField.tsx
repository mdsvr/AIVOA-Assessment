import type { ReactNode } from 'react'

export function FormField({ label, suffix, children }: { label: string; suffix?: string; children: ReactNode }) {
  return (
    <label className="form-field">
      <span className="form-field-label">{label}</span>
      <div className={`form-field-control${suffix ? ' form-field-control-suffixed' : ''}`}>
        {children}
        {suffix && <span className="form-field-suffix">{suffix}</span>}
      </div>
    </label>
  )
}
