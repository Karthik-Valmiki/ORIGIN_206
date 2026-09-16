import React, { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import { ToastProvider } from './components/ui/Toast'
import { OfficerShell } from './layouts/OfficerShell'
import { AdminShell } from './layouts/AdminShell'
import { Login } from './pages/Login'
import { SkeletonList } from './components/ui/Skeleton'

// ── Lazy-loaded Officer pages ─────────────────
const OfficerHome       = lazy(() => import('./pages/officer/Home').then((m) => ({ default: m.OfficerHome })))
const NewInspection     = lazy(() => import('./pages/officer/NewInspection').then((m) => ({ default: m.NewInspection })))
const Processing        = lazy(() => import('./pages/officer/Processing').then((m) => ({ default: m.Processing })))
const InspectionResult  = lazy(() => import('./pages/officer/InspectionResult').then((m) => ({ default: m.InspectionResult })))
const OfficerHistory    = lazy(() => import('./pages/officer/History').then((m) => ({ default: m.OfficerHistory })))
const OfficerProfile    = lazy(() => import('./pages/officer/Profile').then((m) => ({ default: m.OfficerProfile })))

// ── Lazy-loaded Admin pages ───────────────────
const AdminOverview     = lazy(() => import('./pages/admin/Overview').then((m) => ({ default: m.AdminOverview })))
const AdminInspections  = lazy(() => import('./pages/admin/Inspections').then((m) => ({ default: m.AdminInspections })))
const AdminRules        = lazy(() => import('./pages/admin/Rules').then((m) => ({ default: m.AdminRules })))
const AdminRuleEditor   = lazy(() => import('./pages/admin/RuleEditor').then((m) => ({ default: m.AdminRuleEditor })))
const AdminUsers        = lazy(() => import('./pages/admin/Users').then((m) => ({ default: m.AdminUsers })))
const AdminAudit        = lazy(() => import('./pages/admin/Audit').then((m) => ({ default: m.AdminAudit })))
const AdminProfile      = lazy(() => import('./pages/admin/Profile').then((m) => ({ default: m.AdminProfile })))

function PageFallback() {
  return (
    <div style={{ padding: 'var(--space-6)' }}>
      <SkeletonList count={4} />
    </div>
  )
}

// ── Route guards ──────────────────────────────
function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) return <PageFallback />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { hasRole, isLoading, isAuthenticated } = useAuth()
  if (isLoading) return <PageFallback />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!hasRole('ADMIN')) return <Navigate to="/officer/home" replace />
  return children
}

function RedirectIfAuthed() {
  const { isAuthenticated, isLoading, hasRole } = useAuth()
  if (isLoading) return <PageFallback />
  if (isAuthenticated) {
    return <Navigate to={hasRole('ADMIN') ? '/admin/overview' : '/officer/home'} replace />
  }
  return <Login />
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            {/* Public */}
            <Route path="/login" element={<RedirectIfAuthed />} />
            <Route path="/" element={<Navigate to="/login" replace />} />

            {/* Officer */}
            <Route
              path="/officer"
              element={<RequireAuth><OfficerShell /></RequireAuth>}
            >
              <Route index element={<Navigate to="home" replace />} />
              <Route path="home" element={<OfficerHome />} />
              <Route path="inspect" element={<NewInspection />} />
              <Route path="inspect/:id/processing" element={<Processing />} />
              <Route path="inspect/:id/result" element={<InspectionResult />} />
              <Route path="history" element={<OfficerHistory />} />
              <Route path="profile" element={<OfficerProfile />} />
            </Route>

            {/* Admin */}
            <Route
              path="/admin"
              element={<RequireAdmin><AdminShell /></RequireAdmin>}
            >
              <Route index element={<Navigate to="overview" replace />} />
              <Route path="overview" element={<AdminOverview />} />
              <Route path="inspections" element={<AdminInspections />} />
              <Route path="inspections/:id" element={<InspectionResult />} />
              <Route path="rules" element={<AdminRules />} />
              <Route path="rules/:id" element={<AdminRuleEditor />} />
              <Route path="rules/new" element={<AdminRuleEditor />} />
              <Route path="users" element={<AdminUsers />} />
              <Route path="audit" element={<AdminAudit />} />
              <Route path="profile" element={<AdminProfile />} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </Suspense>
      </ToastProvider>
    </BrowserRouter>
  )
}
