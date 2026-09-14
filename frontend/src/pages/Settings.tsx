import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api, authApi } from '../api/client'
import SetupWizard, { type WizardStep } from '../components/SetupWizard'
import type { Theme } from '../types'

const GMAIL_STEPS: WizardStep[] = [
  {
    title: 'Turn on 2-Step Verification',
    body: (
      <p>
        App Passwords require 2-Step Verification on your Google account. If you don't already
        have it on, turn it on at{' '}
        <a href="https://myaccount.google.com/security" target="_blank" rel="noreferrer">
          myaccount.google.com/security
        </a>
        , under "How you sign in to Google".
      </p>
    ),
  },
  {
    title: 'Create an app password',
    body: (
      <p>
        Go to{' '}
        <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer">
          myaccount.google.com/apppasswords
        </a>{' '}
        (you may be asked to sign in again). Enter a name like "Package Tracker" and click
        Create. Google shows you a 16-character password — copy it now, it's only shown once.
      </p>
    ),
  },
]

const UPS_STEPS: WizardStep[] = [
  {
    title: 'Create a UPS.com account',
    body: (
      <p>
        If you don't already have a free account, create one at{' '}
        <a href="https://www.ups.com/" target="_blank" rel="noreferrer">
          ups.com
        </a>
        . You'll need it to register a developer app.
      </p>
    ),
  },
  {
    title: 'Add an app in the Developer Portal',
    body: (
      <p>
        Log in at{' '}
        <a href="https://developer.ups.com/" target="_blank" rel="noreferrer">
          developer.ups.com
        </a>
        , click <strong>My Apps</strong>, then <strong>Add Apps</strong>.
      </p>
    ),
  },
  {
    title: 'Configure the app',
    body: (
      <p>
        Pick a purpose, select your UPS account, and click Next. Under Products, add{' '}
        <strong>Tracking</strong> (plus anything else you want). Leave the Callback URL blank,
        accept the terms, and save.
      </p>
    ),
  },
  {
    title: 'Copy your credentials',
    body: (
      <p>
        Open the app you just created — the <strong>Client ID</strong> and{' '}
        <strong>Client Secret</strong> are shown there.
      </p>
    ),
  },
]

const FEDEX_STEPS: WizardStep[] = [
  {
    title: 'Create a FedEx account',
    body: (
      <p>
        If you don't already have one, create a free account at{' '}
        <a href="https://www.fedex.com/" target="_blank" rel="noreferrer">
          fedex.com
        </a>{' '}
        — it gives you an account number the developer portal will ask for.
      </p>
    ),
  },
  {
    title: 'Create an organization',
    body: (
      <p>
        Sign in at{' '}
        <a href="https://developer.fedex.com/" target="_blank" rel="noreferrer">
          developer.fedex.com
        </a>{' '}
        and create an Organization if you don't already have one.
      </p>
    ),
  },
  {
    title: 'Create a project',
    body: (
      <p>
        Go to <strong>My Projects</strong> → <strong>Create New Project</strong>. Pick a reason
        for the API and give the project a name.
      </p>
    ),
  },
  {
    title: 'Add the Track API',
    body: (
      <p>
        Select the <strong>Track API</strong> for your project.
      </p>
    ),
  },
  {
    title: 'Use the production keys',
    body: (
      <p>
        The project page first shows a <strong>Test key</strong> tab — that won't return real
        tracking data. Open the <strong>Production key</strong> tab and click{' '}
        <strong>Generate Secret Key</strong> to get the real API Key and Secret Key.
      </p>
    ),
  },
]

const USPS_STEPS: WizardStep[] = [
  {
    title: 'Create a USPS Business Account',
    body: (
      <p>
        This is different from a normal USPS.com login. If you don't have one, register at{' '}
        <a
          href="https://catpx-custreg.usps.com/entreg/RegistrationAction_input"
          target="_blank"
          rel="noreferrer"
        >
          USPS business registration
        </a>
        .
      </p>
    ),
  },
  {
    title: 'Register an app',
    body: (
      <p>
        Log in at{' '}
        <a href="https://developers.usps.com/" target="_blank" rel="noreferrer">
          developers.usps.com
        </a>
        , select <strong>Apps</strong> in the menu, and register a new app (any unique app name
        works). Leave the Callback URL blank.
      </p>
    ),
  },
  {
    title: 'Copy your credentials',
    body: (
      <p>
        Open the app you just registered and copy the <strong>Consumer Key</strong> and{' '}
        <strong>Consumer Secret</strong>. Tracking access is included by default.
      </p>
    ),
  },
]

const DHL_STEPS: WizardStep[] = [
  {
    title: 'Register a developer account',
    body: (
      <p>
        Go to{' '}
        <a href="https://developer.dhl.com/user/register" target="_blank" rel="noreferrer">
          developer.dhl.com/user/register
        </a>
        , fill in your details, then follow the email DHL sends you to verify your address and
        set a password.
      </p>
    ),
  },
  {
    title: 'Create an app',
    body: (
      <p>
        Log in, go to <strong>Apps</strong> → <strong>Create App</strong>, and give it a name.
      </p>
    ),
  },
  {
    title: 'Add the tracking API',
    body: (
      <p>
        Edit your app, open <strong>Select APIs</strong>, find{' '}
        <strong>Shipment Tracking – Unified</strong>, and add it. Save to submit the request —
        DHL reviews it, usually quickly.
      </p>
    ),
  },
  {
    title: 'Copy your API key',
    body: (
      <p>
        Open your app and copy the <strong>Consumer Key</strong> (not the Consumer Secret — this
        API only needs the key).
      </p>
    ),
  },
]

const DISCORD_STEPS: WizardStep[] = [
  {
    title: "Open your server's integration settings",
    body: (
      <p>
        In Discord, go to your server → <strong>Server Settings</strong> →{' '}
        <strong>Integrations</strong>.
      </p>
    ),
  },
  {
    title: 'Create a webhook',
    body: (
      <p>
        Click <strong>Webhooks</strong> → <strong>New Webhook</strong>. Name it (e.g. "Package
        Tracker") and pick which channel delivery notifications should post to.
      </p>
    ),
  },
  {
    title: 'Copy the webhook URL',
    body: (
      <p>
        Click <strong>Copy Webhook URL</strong>, then paste it into the field below.
      </p>
    ),
  },
]

type Tab = 'general' | 'connections' | 'account'

const CARRIER_FIELD_KEYS: Record<string, string[]> = {
  UPS: ['ups_client_id', 'ups_client_secret'],
  FedEx: ['fedex_client_id', 'fedex_client_secret'],
  USPS: ['usps_consumer_key', 'usps_consumer_secret'],
  DHL: ['dhl_api_key'],
}

function emptyValuesFor(keys: string[]): Record<string, string> {
  return Object.fromEntries(keys.map((k) => [k, '']))
}

export default function SettingsPage({ onLoggedOut }: { onLoggedOut: () => void }) {
  const queryClient = useQueryClient()
  const { data: settings } = useQuery({ queryKey: ['settings'], queryFn: api.getSettings })
  const [tab, setTab] = useState<Tab>('general')

  const [scanMinutes, setScanMinutes] = useState('')
  const [refreshHours, setRefreshHours] = useState('')

  useEffect(() => {
    if (settings) {
      setScanMinutes(String(settings.email_scan_interval_minutes))
      setRefreshHours(String(settings.tracking_refresh_interval_hours))
    }
  }, [settings])

  const save = useMutation({
    mutationFn: (data: Parameters<typeof api.updateSettings>[0]) => api.updateSettings(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['settings'] }),
  })

  const testDiscord = useMutation({ mutationFn: api.testDiscord })
  const testGmail = useMutation({ mutationFn: api.testGmail })
  const testUps = useMutation({ mutationFn: () => api.testCarrier('UPS') })
  const testFedex = useMutation({ mutationFn: () => api.testCarrier('FedEx') })
  const testUsps = useMutation({ mutationFn: () => api.testCarrier('USPS') })
  const testDhl = useMutation({ mutationFn: () => api.testCarrier('DHL') })

  const changePassword = useMutation({
    mutationFn: (vars: { current_password: string; new_password: string }) =>
      authApi.changePassword(vars.current_password, vars.new_password),
  })
  const logout = useMutation({ mutationFn: authApi.logout, onSuccess: onLoggedOut })

  if (!settings) return <p>Loading…</p>

  return (
    <div className="settings">
      <nav className="settings-tabs">
        <button className={tab === 'general' ? 'active' : ''} onClick={() => setTab('general')}>
          General
        </button>
        <button className={tab === 'connections' ? 'active' : ''} onClick={() => setTab('connections')}>
          Connections
        </button>
        <button className={tab === 'account' ? 'active' : ''} onClick={() => setTab('account')}>
          Account
        </button>
      </nav>

      {tab === 'general' && (
        <>
          <section>
            <h2>Scan intervals</h2>
            <label>
              Email scan interval (minutes)
              <input value={scanMinutes} onChange={(e) => setScanMinutes(e.target.value)} />
            </label>
            <label>
              Tracking refresh interval (hours)
              <input value={refreshHours} onChange={(e) => setRefreshHours(e.target.value)} />
            </label>
            <button
              onClick={() =>
                save.mutate({
                  email_scan_interval_minutes: Number(scanMinutes),
                  tracking_refresh_interval_hours: Number(refreshHours),
                })
              }
              disabled={save.isPending}
            >
              Save intervals
            </button>
          </section>

          <section>
            <h2>Appearance</h2>
            <div className="theme-toggle">
              {(['system', 'light', 'dark'] as Theme[]).map((t) => (
                <button
                  key={t}
                  className={settings.theme === t ? 'active' : ''}
                  onClick={() => save.mutate({ theme: t })}
                  disabled={save.isPending}
                >
                  {t[0].toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
          </section>

          <section>
            <h2>Last run</h2>
            <p className="muted">Last email scan: {settings.last_email_scan_at ?? 'never'}</p>
            <p className="muted">Last tracking refresh: {settings.last_tracking_refresh_at ?? 'never'}</p>
          </section>
        </>
      )}

      {tab === 'connections' && (
        <>
          <SetupWizard
            title="Gmail"
            configured={settings.gmail_configured}
            extraStatus={
              settings.gmail_last_error && <p className="error">Last error: {settings.gmail_last_error}</p>
            }
            steps={GMAIL_STEPS}
            fields={[
              { key: 'gmail_address', label: 'Gmail address', placeholder: 'you@gmail.com' },
              { key: 'gmail_app_password', label: '16-character app password' },
            ]}
            saving={save.isPending}
            onSave={(values) => save.mutate(values)}
            onRemove={() => save.mutate(emptyValuesFor(['gmail_address', 'gmail_app_password']))}
            onTest={() => testGmail.mutate()}
            testing={testGmail.isPending}
            testResult={testGmail.data}
          />

          <section style={{ background: 'transparent', border: 'none', padding: 0 }}>
            <h2>Carrier tracking</h2>
            <p className="muted">
              Each carrier's own free developer API is used directly — no third-party tracking
              aggregator. Set up the carriers you actually ship with; packages from carriers you
              haven't configured just won't refresh.
            </p>
          </section>

          <SetupWizard
            title="UPS"
            configured={settings.ups_configured}
            steps={UPS_STEPS}
            fields={[
              { key: 'ups_client_id', label: 'Client ID' },
              { key: 'ups_client_secret', label: 'Client secret' },
            ]}
            saving={save.isPending}
            onSave={(values) => save.mutate(values)}
            onRemove={() => save.mutate(emptyValuesFor(CARRIER_FIELD_KEYS.UPS))}
            onTest={() => testUps.mutate()}
            testing={testUps.isPending}
            testResult={testUps.data}
          />

          <SetupWizard
            title="FedEx"
            configured={settings.fedex_configured}
            steps={FEDEX_STEPS}
            fields={[
              { key: 'fedex_client_id', label: 'API key (client ID)' },
              { key: 'fedex_client_secret', label: 'Secret key' },
            ]}
            saving={save.isPending}
            onSave={(values) => save.mutate(values)}
            onRemove={() => save.mutate(emptyValuesFor(CARRIER_FIELD_KEYS.FedEx))}
            onTest={() => testFedex.mutate()}
            testing={testFedex.isPending}
            testResult={testFedex.data}
          />

          <SetupWizard
            title="USPS"
            configured={settings.usps_configured}
            steps={USPS_STEPS}
            fields={[
              { key: 'usps_consumer_key', label: 'Consumer key' },
              { key: 'usps_consumer_secret', label: 'Consumer secret' },
            ]}
            saving={save.isPending}
            onSave={(values) => save.mutate(values)}
            onRemove={() => save.mutate(emptyValuesFor(CARRIER_FIELD_KEYS.USPS))}
            onTest={() => testUsps.mutate()}
            testing={testUsps.isPending}
            testResult={testUsps.data}
          />

          <SetupWizard
            title="DHL"
            configured={settings.dhl_configured}
            steps={DHL_STEPS}
            fields={[{ key: 'dhl_api_key', label: 'API key' }]}
            saving={save.isPending}
            onSave={(values) => save.mutate(values)}
            onRemove={() => save.mutate(emptyValuesFor(CARRIER_FIELD_KEYS.DHL))}
            onTest={() => testDhl.mutate()}
            testing={testDhl.isPending}
            testResult={testDhl.data}
          />

          <SetupWizard
            title="Discord notifications"
            configured={settings.discord_webhook_url_set}
            steps={DISCORD_STEPS}
            fields={[{ key: 'discord_webhook_url', label: 'Webhook URL' }]}
            saving={save.isPending}
            onSave={(values) => save.mutate(values)}
            onRemove={() => save.mutate({ discord_webhook_url: '' })}
            onTest={() => testDiscord.mutate()}
            testing={testDiscord.isPending}
            testResult={testDiscord.data}
          />

          {settings.discord_webhook_url_set && (
            <section>
              <h2>Discord notification types</h2>
              <p className="muted">Choose which events post to your Discord webhook.</p>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={settings.notify_delivered}
                  onChange={(e) => save.mutate({ notify_delivered: e.target.checked })}
                />
                Package delivered
              </label>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={settings.notify_exception}
                  onChange={(e) => save.mutate({ notify_exception: e.target.checked })}
                />
                Delivery exception / problem
              </label>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={settings.notify_new_package}
                  onChange={(e) => save.mutate({ notify_new_package: e.target.checked })}
                />
                New package found in email
              </label>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={settings.notify_gmail_errors}
                  onChange={(e) => save.mutate({ notify_gmail_errors: e.target.checked })}
                />
                Gmail connection errors
              </label>
            </section>
          )}
        </>
      )}

      {tab === 'account' && <AccountTab changePassword={changePassword} logout={logout} />}
    </div>
  )
}

function AccountTab({
  changePassword,
  logout,
}: {
  changePassword: ReturnType<
    typeof useMutation<{ ok: boolean }, Error, { current_password: string; new_password: string }>
  >
  logout: ReturnType<typeof useMutation<{ ok: boolean }, Error, void>>
}) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [formError, setFormError] = useState('')

  return (
    <section>
      <h2>Change password</h2>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (next !== confirm) {
            setFormError('New passwords do not match')
            return
          }
          setFormError('')
          changePassword.mutate(
            { current_password: current, new_password: next },
            {
              onSuccess: () => {
                setCurrent('')
                setNext('')
                setConfirm('')
              },
            },
          )
        }}
      >
        <label>
          Current password
          <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} />
        </label>
        <label>
          New password
          <input type="password" value={next} onChange={(e) => setNext(e.target.value)} />
        </label>
        <label>
          Confirm new password
          <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </label>
        {formError && <p className="error">{formError}</p>}
        {changePassword.isError && <p className="error">{(changePassword.error as Error).message}</p>}
        {changePassword.isSuccess && <p className="success">Password changed.</p>}
        <button type="submit" disabled={!current || !next || changePassword.isPending}>
          Change password
        </button>
      </form>

      <h2>Session</h2>
      <button onClick={() => logout.mutate()} disabled={logout.isPending}>
        Log out
      </button>
    </section>
  )
}
