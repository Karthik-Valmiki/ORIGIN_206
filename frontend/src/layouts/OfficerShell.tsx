import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Home, Camera, Clock, User, LogOut } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import styles from './OfficerShell.module.css'

const NAV = [
  { to: '/officer/home',    icon: Home,   label: 'Home'    },
  { to: '/officer/inspect', icon: Camera, label: 'Inspect' },
  { to: '/officer/history', icon: Clock,  label: 'History' },
  { to: '/officer/profile', icon: User,   label: 'Profile' },
]

export function OfficerShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className={styles.shell}>
      {/* Desktop sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarBrand}>
          <span className={styles.brandMark}>LM</span>
          <span className={styles.brandName}>Inspect</span>
        </div>
        <nav className={styles.sidebarNav} aria-label="Primary navigation">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                [styles.sidebarLink, isActive ? styles.active : ''].filter(Boolean).join(' ')
              }
            >
              <Icon size={20} aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className={styles.sidebarFooter}>
          <span className={styles.sidebarUser}>{user?.full_name}</span>
          <button className={styles.logoutBtn} onClick={handleLogout} aria-label="Sign out">
            <LogOut size={18} />
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className={styles.main}>
        <Outlet />
      </main>

      {/* Mobile bottom navigation */}
      <nav className={styles.bottomNav} aria-label="Primary navigation">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              [styles.bottomLink, isActive ? styles.active : ''].filter(Boolean).join(' ')
            }
          >
            <Icon size={22} aria-hidden="true" />
            <span className={styles.bottomLabel}>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
