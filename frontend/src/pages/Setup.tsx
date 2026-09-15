import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { authApi } from '../api/client'

export default function Setup({ onDone }: { onDone: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: () => authApi.setup(username.trim(), password),
    onSuccess: onDone,
    onError: (e: Error) => setError(e.message),
  })

  return (
    <div className="auth-screen">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (password !== confirm) {
            setError('Passwords do not match')
            return
          }
          setError('')
          mutation.mutate()
        }}
      >
        <h1>📦 Package Tracker</h1>
        <p className="muted">
          Create the admin account. This runs once — sign-ups are disabled after this account is
          created.
        </p>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        <label>
          Confirm password
          <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" className="primary" disabled={!username || !password || mutation.isPending}>
          Create account
        </button>
      </form>
    </div>
  )
}
