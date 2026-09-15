import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import StatusBadge from '../components/StatusBadge'

export default function PackageDetailPage() {
  const { id } = useParams()
  const packageId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: pkg, isLoading } = useQuery({
    queryKey: ['package', packageId],
    queryFn: () => api.getPackage(packageId),
  })
  const [name, setName] = useState('')

  const rename = useMutation({
    mutationFn: (item_name: string) => api.updatePackage(packageId, { item_name }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['package', packageId] }),
  })
  const archive = useMutation({
    mutationFn: () => api.updatePackage(packageId, { archived: true }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['packages'] }),
  })
  const remove = useMutation({
    mutationFn: () => api.deletePackage(packageId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['packages'] })
      navigate('/')
    },
  })

  if (isLoading || !pkg) return <p>Loading…</p>

  return (
    <div className="detail">
      <Link to="/">&larr; Back to map</Link>
      <h2>
        {pkg.item_name} <StatusBadge status={pkg.status} />
      </h2>
      <p className="muted">
        {pkg.tracking_number} {pkg.carrier ? `· ${pkg.carrier}` : ''}
      </p>

      {pkg.last_error && (
        <div className="error-banner">
          <strong>⚠ Tracking refresh is failing:</strong> {pkg.last_error}
          {pkg.last_error_at && (
            <div className="muted">Since {new Date(pkg.last_error_at).toLocaleString()}</div>
          )}
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (name.trim()) rename.mutate(name.trim())
        }}
      >
        <input placeholder="Rename item" value={name} onChange={(e) => setName(e.target.value)} />
        <button type="submit" disabled={rename.isPending}>
          Rename
        </button>
      </form>

      <div className="detail-actions">
        <button onClick={() => archive.mutate()} disabled={archive.isPending}>
          Archive
        </button>
        <button
          onClick={() => {
            if (confirm('Delete this package?')) remove.mutate()
          }}
          disabled={remove.isPending}
        >
          Delete
        </button>
      </div>

      <h3>History</h3>
      <ul className="event-list">
        {pkg.events
          .slice()
          .reverse()
          .map((ev) => (
            <li key={ev.id}>
              <div>{ev.event_time ? new Date(ev.event_time).toLocaleString() : 'Unknown time'}</div>
              <div>{ev.location_text ?? 'Unknown location'}</div>
              <div className="muted">{ev.description}</div>
            </li>
          ))}
        {pkg.events.length === 0 && <p className="muted">No scan history yet.</p>}
      </ul>
    </div>
  )
}
