import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import styles from './Login.module.css'

function getErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const r = (err as { response?: { data?: { detail?: string }; status?: number } }).response
    if (r?.status === 401) return 'Incorrect email or password. Please try again.'
    if (r?.status === 400) return r.data?.detail ?? 'Account issue. Contact your administrator.'
    if (r?.status && r.status >= 500) return 'Server error. Please try again in a moment.'
  }
  return 'Unable to sign in. Check your connection and try again.'
}

export function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
      // AuthContext already fetched /me → check role
      navigate('/officer/home', { replace: true })
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.header}>
          <div className={styles.logoMark}>LM</div>
          <h1 className={styles.title}>LM Inspect</h1>
          <p className={styles.subtitle}>
            Legal Metrology Compliance Verification
          </p>
        </div>

        <form onSubmit={handleSubmit} className={styles.form} noValidate>
          <Input
            label="Email address"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            placeholder="officer@dept.gov.in"
            id="login-email"
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            placeholder="••••••••"
            id="login-password"
          />

          {error && (
            <p className={styles.errorMsg} role="alert">
              {error}
            </p>
          )}

          <Button
            type="submit"
            fullWidth
            size="lg"
            loading={loading}
            id="login-submit"
          >
            Sign in
          </Button>
        </form>

        <p className={styles.footer}>
          Authorised personnel only.
          Contact your administrator for access.
        </p>
      </div>
    </div>
  )
}
