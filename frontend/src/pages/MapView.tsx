import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import L from 'leaflet'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import { api } from '../api/client'
import StatusBadge from '../components/StatusBadge'

const defaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
})

export default function MapView() {
  const queryClient = useQueryClient()
  const { data: packages, isLoading } = useQuery({
    queryKey: ['packages'],
    queryFn: () => api.listPackages(),
    refetchInterval: 60000,
  })
  const [addOpen, setAddOpen] = useState(false)

  const scanNow = useMutation({
    mutationFn: api.scanNow,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['packages'] }),
  })
  const refreshNow = useMutation({
    mutationFn: api.refreshNow,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['packages'] }),
  })

  const located = (packages ?? []).filter((p) => p.last_lat != null && p.last_lon != null)

  return (
    <div className="map-layout">
      <aside className="sidebar">
        <div className="sidebar-actions">
          <button onClick={() => scanNow.mutate()} disabled={scanNow.isPending}>
            {scanNow.isPending ? 'Scanning…' : 'Scan emails now'}
          </button>
          <button onClick={() => refreshNow.mutate()} disabled={refreshNow.isPending}>
            {refreshNow.isPending ? 'Refreshing…' : 'Refresh tracking now'}
          </button>
          <button onClick={() => setAddOpen((v) => !v)}>+ Add tracking number</button>
        </div>
        {addOpen && <AddPackageForm onDone={() => setAddOpen(false)} />}
        {isLoading && <p>Loading…</p>}
        <ul className="package-list">
          {(packages ?? []).map((p) => (
            <li key={p.id}>
              <Link to={`/packages/${p.id}`}>
                <strong>{p.item_name}</strong>
                <StatusBadge status={p.status} />
                <div className="muted">
                  {p.tracking_number}
                  {p.carrier ? ` · ${p.carrier}` : ''}
                </div>
                <div className="muted">{p.last_location_text ?? 'No location yet'}</div>
              </Link>
            </li>
          ))}
          {packages && packages.length === 0 && (
            <p className="muted">No packages yet. Add one, or connect Gmail in Settings.</p>
          )}
        </ul>
      </aside>
      <MapContainer center={[20, 0]} zoom={2} minZoom={2} worldCopyJump className="map-container">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {located.map((p) => (
          <Marker key={p.id} position={[p.last_lat as number, p.last_lon as number]} icon={defaultIcon}>
            <Popup>
              <strong>{p.item_name}</strong>
              <br />
              {p.tracking_number} {p.carrier ? `(${p.carrier})` : ''}
              <br />
              <StatusBadge status={p.status} />
              <br />
              {p.last_location_text}
              <br />
              <Link to={`/packages/${p.id}`}>View history</Link>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}

function AddPackageForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient()
  const [trackingNumber, setTrackingNumber] = useState('')
  const [itemName, setItemName] = useState('')
  const create = useMutation({
    mutationFn: () =>
      api.createPackage({ tracking_number: trackingNumber, item_name: itemName || trackingNumber }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['packages'] })
      onDone()
    },
  })
  return (
    <form
      className="add-form"
      onSubmit={(e) => {
        e.preventDefault()
        create.mutate()
      }}
    >
      <input
        placeholder="Tracking number"
        value={trackingNumber}
        onChange={(e) => setTrackingNumber(e.target.value)}
        required
      />
      <input
        placeholder="Item name (optional)"
        value={itemName}
        onChange={(e) => setItemName(e.target.value)}
      />
      <button type="submit" disabled={create.isPending}>
        Add
      </button>
      {create.isError && <p className="error">{(create.error as Error).message}</p>}
    </form>
  )
}
