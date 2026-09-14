export interface TrackingEvent {
  id: number
  event_time: string | null
  location_text: string | null
  lat: number | null
  lon: number | null
  description: string | null
  raw_status: string | null
}

export interface Package {
  id: number
  tracking_number: string
  carrier: string | null
  item_name: string
  status: 'in_transit' | 'delivered' | 'exception' | 'unknown'
  last_lat: number | null
  last_lon: number | null
  last_location_text: string | null
  last_update_at: string | null
  archived: boolean
  created_at: string
}

export interface PackageDetail extends Package {
  events: TrackingEvent[]
}

export type Theme = 'system' | 'light' | 'dark'

export interface Settings {
  email_scan_interval_minutes: number
  tracking_refresh_interval_hours: number
  discord_webhook_url_set: boolean
  last_email_scan_at: string | null
  last_tracking_refresh_at: string | null
  gmail_configured: boolean
  gmail_last_error: string | null
  ups_configured: boolean
  fedex_configured: boolean
  usps_configured: boolean
  dhl_configured: boolean
  amazon_configured: boolean
  theme: Theme
  notify_delivered: boolean
  notify_exception: boolean
  notify_out_for_delivery: boolean
  notify_new_package: boolean
  notify_gmail_errors: boolean
}
