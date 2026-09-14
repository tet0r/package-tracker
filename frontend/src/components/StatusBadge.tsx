const LABELS: Record<string, string> = {
  in_transit: 'In transit',
  delivered: 'Delivered',
  exception: 'Exception',
  unknown: 'Unknown',
}

export default function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{LABELS[status] ?? status}</span>
}
