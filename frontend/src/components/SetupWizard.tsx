import { useState, type ReactNode } from 'react'

export interface WizardStep {
  title: string
  body: ReactNode
}

export interface WizardField {
  key: string
  label: string
  placeholder?: string
}

export default function SetupWizard({
  title,
  configured,
  extraStatus,
  steps,
  fields,
  onSave,
  saving,
  onRemove,
  onTest,
  testing,
  testResult,
}: {
  title: string
  configured: boolean
  extraStatus?: ReactNode
  steps: WizardStep[]
  fields: WizardField[]
  onSave: (values: Record<string, string>) => void
  saving: boolean
  onRemove?: () => void
  onTest?: () => void
  testing?: boolean
  testResult?: { ok: boolean; error?: string } | undefined
}) {
  const [open, setOpen] = useState(!configured)
  const [stepIndex, setStepIndex] = useState(0)
  const [values, setValues] = useState<Record<string, string>>({})

  const totalSteps = steps.length + 1
  const onCredentialsStep = stepIndex === steps.length
  const allFilled = fields.every((f) => values[f.key]?.trim())

  return (
    <section className="wizard-section">
      <div className="wizard-header">
        <h2>
          {title}{' '}
          <span className={`badge badge-${configured ? 'delivered' : 'unknown'}`}>
            {configured ? 'Configured' : 'Not set'}
          </span>
        </h2>
        <button
          type="button"
          onClick={() => {
            setOpen((o) => !o)
            setStepIndex(0)
          }}
        >
          {open ? 'Hide' : configured ? 'Reconfigure' : 'Set up'}
        </button>
      </div>
      {extraStatus}

      {open && (
        <div className="wizard-body">
          <div className="muted">
            Step {stepIndex + 1} of {totalSteps}
          </div>

          {onCredentialsStep ? (
            <div className="wizard-step">
              <h3>Enter your credentials</h3>
              {fields.map((f) => (
                <input
                  key={f.key}
                  type="password"
                  placeholder={f.placeholder ?? f.label}
                  value={values[f.key] ?? ''}
                  onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                />
              ))}
              <div className="wizard-nav">
                <button type="button" onClick={() => setStepIndex((i) => Math.max(0, i - 1))}>
                  Back
                </button>
                <button type="button" onClick={() => onSave(values)} disabled={!allFilled || saving}>
                  Save
                </button>
                {onTest && (
                  <button type="button" onClick={onTest} disabled={!configured || testing}>
                    Test connection
                  </button>
                )}
                {onRemove && configured && (
                  <button
                    type="button"
                    className="danger"
                    onClick={() => {
                      if (confirm(`Remove your ${title} connection?`)) onRemove()
                    }}
                  >
                    Remove connection
                  </button>
                )}
              </div>
              {testResult && (
                <p className={testResult.ok ? 'success' : 'error'}>
                  {testResult.ok ? 'Connected successfully!' : `Failed: ${testResult.error ?? 'check your credentials'}`}
                </p>
              )}
            </div>
          ) : (
            <div className="wizard-step">
              <h3>{steps[stepIndex].title}</h3>
              <div>{steps[stepIndex].body}</div>
              <div className="wizard-nav">
                {stepIndex > 0 && (
                  <button type="button" onClick={() => setStepIndex((i) => i - 1)}>
                    Back
                  </button>
                )}
                <button type="button" onClick={() => setStepIndex((i) => i + 1)}>
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
