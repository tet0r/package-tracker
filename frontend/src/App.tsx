import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { api, authApi } from './api/client'
import Login from './pages/Login'
import PackageDetailPage from './pages/PackageDetail'
import MapView from './pages/MapView'
import SettingsPage from './pages/Settings'
import Setup from './pages/Setup'

type AuthState = 'loading' | 'setup' | 'login' | 'authed'

export default function App() {
  const [authState, setAuthState] = useState<AuthState>('loading')

  const check = async () => {
    try {
      const status = await authApi.status()
      if (status.setup_required) {
        setAuthState('setup')
        return
      }
      await authApi.me()
      setAuthState('authed')
    } catch {
      setAuthState('login')
    }
  }

  useEffect(() => {
    check()
    const handleUnauthorized = () => setAuthState('login')
    window.addEventListener('auth:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized)
  }, [])

  if (authState === 'loading') return <p className="muted">Loading…</p>
  if (authState === 'setup') return <Setup onDone={() => setAuthState('authed')} />
  if (authState === 'login') return <Login onDone={() => setAuthState('authed')} />

  return <Shell onLoggedOut={() => setAuthState('login')} />
}

function Shell({ onLoggedOut }: { onLoggedOut: () => void }) {
  const { data: settings } = useQuery({ queryKey: ['settings'], queryFn: api.getSettings })

  useEffect(() => {
    if (!settings) return
    if (settings.theme === 'system') {
      document.documentElement.removeAttribute('data-theme')
    } else {
      document.documentElement.setAttribute('data-theme', settings.theme)
    }
  }, [settings?.theme])

  useEffect(() => {
    const handleUnauthorized = () => onLoggedOut()
    window.addEventListener('auth:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized)
  }, [onLoggedOut])

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>📦 Package Tracker</h1>
        <nav>
          <NavLink to="/" end>
            Map
          </NavLink>
          <NavLink to="/settings">Settings</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<MapView />} />
          <Route path="/packages/:id" element={<PackageDetailPage />} />
          <Route path="/settings" element={<SettingsPage onLoggedOut={onLoggedOut} />} />
        </Routes>
      </main>
    </div>
  )
}
