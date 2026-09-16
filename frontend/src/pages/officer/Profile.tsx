import { useAuth } from '../../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import styles from './Profile.module.css'

export function OfficerProfile() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Profile</h1>
      <div className={styles.card}>
        <div className={styles.avatar}>{user?.full_name?.[0]?.toUpperCase() ?? 'O'}</div>
        <div className={styles.info}>
          <p className={styles.name}>{user?.full_name}</p>
          <p className={styles.email}>{user?.email}</p>
          <p className={styles.role}>{user?.roles.join(', ')}</p>
        </div>
      </div>
      <Button
        variant="secondary"
        onClick={() => { logout(); navigate('/login', { replace: true }) }}
        id="btn-officer-logout"
      >
        Sign out
      </Button>
    </div>
  )
}

export function AdminProfile() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Profile</h1>
      <div className={styles.card}>
        <div className={[styles.avatar, styles.adminAvatar].join(' ')}>{user?.full_name?.[0]?.toUpperCase() ?? 'A'}</div>
        <div className={styles.info}>
          <p className={styles.name}>{user?.full_name}</p>
          <p className={styles.email}>{user?.email}</p>
          <p className={styles.role}>{user?.roles.join(', ')}</p>
        </div>
      </div>
      <Button
        variant="secondary"
        onClick={() => { logout(); navigate('/login', { replace: true }) }}
        id="btn-admin-logout"
      >
        Sign out
      </Button>
    </div>
  )
}
