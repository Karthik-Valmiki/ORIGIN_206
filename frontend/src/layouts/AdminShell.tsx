import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { LayoutDashboard, ClipboardList, BookOpen, Users, ScrollText, User, LogOut } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import styles from './AdminShell.module.css'

const NAV = [
  { to: '/admin/overview',     icon: LayoutDashboard, label: 'Overview'     },
  { to: '/admin/inspections',  icon: ClipboardList,   label: 'Inspections'  },
  { to: '/admin/rules',        icon: BookOpen,        label: 'Rules'        },
  { to: '/admin/users',        icon: Users,           label: 'Users'        },
  { to: '/admin/audit',        icon: ScrollText,      label: 'Audit'        },
  { to: '/admin/profile',      icon: User,            label: 'Profile'      },
]

export function AdminShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.brandMark}>LM</span>
          <div>
            <div className={styles.brandName}>Inspect</div>
            <div className={styles.brandRole}>Admin Console</div>
          </div>
        </div>
        <nav className={styles.nav} aria-label="Admin navigation">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                [styles.link, isActive ? styles.active : ''].filter(Boolean).join(' ')
              }
            >
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className={styles.footer}>
          <div className={styles.footerUser}>
            <span className={styles.footerName}>{user?.full_name}</span>
            <span className={styles.footerEmail}>{user?.email}</span>
          </div>
          <button className={styles.logoutBtn} onClick={handleLogout} aria-label="Sign out">
            <LogOut size={18} />
          </button>
        </div>
      </aside>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}
