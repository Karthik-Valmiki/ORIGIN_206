import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Camera, Clock } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { listInspections, type Inspection } from '../../api/inspections'
import { Card } from '../../components/ui/Card'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { Button } from '../../components/ui/Button'
import { SkeletonList } from '../../components/ui/Skeleton'
import { EmptyState } from '../../components/ui/EmptyState'
import styles from './Home.module.css'

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

function InspectionRow({ inspection, onClick }: { inspection: Inspection; onClick: () => void }) {
  return (
    <Card clickable onClick={onClick} padding="md">
      <div className={styles.rowTop}>
        <span className={styles.rowId}>{inspection.inspection_number}</span>
        <StatusBadge status={inspection.status} size="sm" />
      </div>
      <div className={styles.rowBottom}>
        <span className={styles.rowCategory}>{inspection.category_name ?? 'Unknown category'}</span>
        <span className={styles.rowDate}>{formatDate(inspection.created_at)}</span>
      </div>
    </Card>
  )
}

export function OfficerHome() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['inspections', 'officer', 'recent'],
    queryFn: () => listInspections(0, 20),
    refetchInterval: 10_000, // refresh every 10s for live processing updates
  })

  const inspections = data?.data ?? []
  const processing  = inspections.filter((i) => i.status === 'PENDING' || i.status === 'PROCESSING')
  const needsReview = inspections.filter((i) => i.status === 'REVIEW_REQUIRED')
  const recent      = inspections.filter((i) => !['PENDING','PROCESSING','REVIEW_REQUIRED'].includes(i.status)).slice(0, 5)

  function openInspection(i: Inspection) {
    if (i.status === 'PENDING' || i.status === 'PROCESSING') {
      navigate(`/officer/inspect/${i.id}/processing`)
    } else {
      navigate(`/officer/inspect/${i.id}/result`)
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.greeting}>{greeting()}</p>
          <h1 className={styles.name}>{user?.full_name}</h1>
        </div>
      </header>

      {/* Primary action */}
      <section className={styles.primaryAction}>
        <Button
          size="lg"
          fullWidth
          onClick={() => navigate('/officer/inspect')}
          id="btn-start-inspection"
        >
          <Camera size={22} aria-hidden="true" />
          Start Inspection
        </Button>
        <p className={styles.actionHint}>Scan a product label to verify compliance</p>
      </section>

      {/* Processing */}
      {isLoading ? (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Processing</h2>
          <SkeletonList count={2} />
        </section>
      ) : processing.length > 0 ? (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Currently processing</h2>
          <div className={styles.list}>
            {processing.map((i) => (
              <InspectionRow key={i.id} inspection={i} onClick={() => openInspection(i)} />
            ))}
          </div>
        </section>
      ) : null}

      {/* Needs review */}
      {needsReview.length > 0 && (
        <section className={styles.section}>
          <h2 className={[styles.sectionTitle, styles.reviewTitle].join(' ')}>
            ! Requires your review
          </h2>
          <div className={styles.list}>
            {needsReview.map((i) => (
              <InspectionRow key={i.id} inspection={i} onClick={() => openInspection(i)} />
            ))}
          </div>
        </section>
      )}

      {/* Recent */}
      <section className={styles.section}>
        <div className={styles.sectionRow}>
          <h2 className={styles.sectionTitle}>Recent inspections</h2>
          <button className={styles.viewAll} onClick={() => navigate('/officer/history')}>
            <Clock size={14} aria-hidden="true" />
            View all
          </button>
        </div>
        {isLoading ? (
          <SkeletonList count={3} />
        ) : isError ? (
          <p className={styles.errorHint}>Could not load recent inspections. <button onClick={() => refetch()}>Retry</button></p>
        ) : recent.length === 0 ? (
          <EmptyState
            title="No inspections yet"
            description="Start your first product inspection."
            action={{ label: 'Start inspection', onClick: () => navigate('/officer/inspect') }}
          />
        ) : (
          <div className={styles.list}>
            {recent.map((i) => (
              <InspectionRow key={i.id} inspection={i} onClick={() => openInspection(i)} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
