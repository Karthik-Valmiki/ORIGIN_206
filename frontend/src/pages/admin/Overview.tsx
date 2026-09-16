import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { listInspections } from '../../api/inspections'
import { listAuditLog } from '../../api/audit'
import { Card } from '../../components/ui/Card'
import { SkeletonList } from '../../components/ui/Skeleton'
import styles from './Overview.module.css'

export function AdminOverview() {
  const navigate = useNavigate()

  const { data: inspData, isLoading: inspsLoading } = useQuery({
    queryKey: ['inspections', 'admin', 'overview'],
    queryFn: () => listInspections(0, 200),
    refetchInterval: 30_000,
  })

  const { data: auditData, isLoading: auditLoading } = useQuery({
    queryKey: ['audit', 'recent'],
    queryFn: () => listAuditLog(0, 10),
  })

  const inspections = inspData?.data ?? []
  const failedCount = inspections.filter((i) => i.status === 'PROCESSING_FAILED').length
  const reviewCount = inspections.filter((i) => i.status === 'REVIEW_REQUIRED').length
  const processingCount = inspections.filter((i) => i.status === 'PROCESSING' || i.status === 'PENDING').length

  const auditEntries = auditData?.data ?? []

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Admin overview</h1>

      {/* Attention items */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Needs attention</h2>
        {inspsLoading ? (
          <SkeletonList count={3} />
        ) : (
          <div className={styles.attentionGrid}>
            {failedCount > 0 ? (
              <Card clickable onClick={() => navigate('/admin/inspections?status=PROCESSING_FAILED')} padding="md">
                <p className={styles.attentionCount}>{failedCount}</p>
                <p className={[styles.attentionLabel, styles.failed].join(' ')}>Processing failures</p>
              </Card>
            ) : (
              <Card padding="md">
                <p className={styles.allGoodText}>✓ No processing failures</p>
              </Card>
            )}

            {reviewCount > 0 ? (
              <Card clickable onClick={() => navigate('/admin/inspections?status=REVIEW_REQUIRED')} padding="md">
                <p className={styles.attentionCount}>{reviewCount}</p>
                <p className={[styles.attentionLabel, styles.review].join(' ')}>Awaiting review</p>
              </Card>
            ) : (
              <Card padding="md">
                <p className={styles.allGoodText}>✓ No pending reviews</p>
              </Card>
            )}

            {processingCount > 0 && (
              <Card padding="md">
                <p className={styles.attentionCount}>{processingCount}</p>
                <p className={styles.attentionLabel}>Currently processing</p>
              </Card>
            )}
          </div>
        )}
      </section>

      {/* Recent activity */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Recent activity</h2>
        {auditLoading ? (
          <SkeletonList count={5} />
        ) : auditEntries.length === 0 ? (
          <p className={styles.noActivity}>No recent activity.</p>
        ) : (
          <div className={styles.activityList}>
            {auditEntries.map((entry) => (
              <div key={entry.id} className={styles.activityRow}>
                <div className={styles.activityDot} aria-hidden="true" />
                <div className={styles.activityContent}>
                  <span className={styles.activityAction}>{entry.action.replace(/_/g, ' ').toLowerCase()}</span>
                  {entry.user_id && (
                    <span className={styles.activityActor}> · {entry.user_id}</span>
                  )}
                  {entry.entity_name && (
                    <span className={styles.activityActor}> · {entry.entity_name}</span>
                  )}
                  <span className={styles.activityTime}>
                    {' · '}
                    {new Date(entry.created_at).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
