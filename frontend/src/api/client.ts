import type { Package, PackageDetail, Settings } from '../types'

const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    ...options,
  })
  if (res.status === 401) {
    window.dispatchEvent(new Event('auth:unauthorized'))
    throw new Error('Not authenticated')
  }
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  listPackages: (includeArchived = false) =>
    request<Package[]>(`/packages?include_archived=${includeArchived}`),
  getPackage: (id: number) => request<PackageDetail>(`/packages/${id}`),
  createPackage: (data: { tracking_number: string; item_name: string; carrier?: string }) =>
    request<Package>('/packages', { method: 'POST', body: JSON.stringify(data) }),
  updatePackage: (id: number, data: { item_name?: string; archived?: boolean }) =>
    request<Package>(`/packages/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deletePackage: (id: number) => request<void>(`/packages/${id}`, { method: 'DELETE' }),
  scanNow: () => request<{ status: string }>('/packages/scan-now', { method: 'POST' }),
  refreshNow: () => request<{ status: string }>('/packages/refresh-now', { method: 'POST' }),

  getSettings: () => request<Settings>('/settings'),
  updateSettings: (
    data: Partial<{
      email_scan_interval_minutes: number
      tracking_refresh_interval_hours: number
      discord_webhook_url: string
      gmail_address: string
      gmail_app_password: string
      ups_client_id: string
      ups_client_secret: string
      fedex_client_id: string
      fedex_client_secret: string
      usps_consumer_key: string
      usps_consumer_secret: string
      dhl_api_key: string
      amazon_17track_api_key: string
      theme: string
      notify_delivered: boolean
      notify_exception: boolean
      notify_out_for_delivery: boolean
      notify_new_package: boolean
      notify_gmail_errors: boolean
    }>,
  ) => request<Settings>('/settings', { method: 'PUT', body: JSON.stringify(data) }),
  testDiscord: () => request<{ ok: boolean; error?: string }>('/settings/discord/test', { method: 'POST' }),
  testGmail: () => request<{ ok: boolean; error?: string }>('/settings/gmail/test', { method: 'POST' }),
  testCarrier: (carrier: string) =>
    request<{ ok: boolean; error?: string }>(`/settings/carriers/${carrier}/test`, { method: 'POST' }),
}

export const authApi = {
  status: () => request<{ setup_required: boolean }>('/auth/status'),
  me: () => request<{ username: string }>('/auth/me'),
  setup: (username: string, password: string) =>
    request<{ username: string }>('/auth/setup', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  login: (username: string, password: string) =>
    request<{ username: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<{ ok: boolean }>('/auth/logout', { method: 'POST' }),
  changePassword: (current_password: string, new_password: string) =>
    request<{ ok: boolean }>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password }),
    }),
}
