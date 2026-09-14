import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { authApi } from '../api/client'

export default function Login({ onDone }: { onDone: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: () => authApi.login(username.trim(), password),
    onSuccess: onDone,
    onError: (e: Error) => setError(e.message),
  })

  return (
    <div className="auth-screen">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          setError('')
          mutation.mutate()
        }}
      >
        <h1>📦 Package Tracker</h1>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={!username || !password || mutation.isPending}>
          Log in
        </button>
      </form>
    </div>
  )
}
