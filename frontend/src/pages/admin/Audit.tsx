import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listAuditLog } from '../../api/audit'
import { SkeletonList } from '../../components/ui/Skeleton'
import { ErrorState } from '../../components/ui/EmptyState'
import styles from './Audit.module.css'

const PAGE_SIZE = 50

const ACTION_LABELS: Record<string, string> = {
  CREATE_INSPECTION: 'Created inspection',
  RETRY_INSPECTION_WITH_IMAGES: 'Re-uploaded images',
  SUBMIT_REVIEW: 'Submitted review',
  CREATE_USER: 'Created user',
  DEACTIVATE_USER: 'Deactivated user',
  ACTIVATE_USER: 'Activated user',
  CREATE_RULE: 'Created rule',
  PUBLISH_RULE: 'Published rule',
}

function humanAction(action: string) {
  return ACTION_LABELS[action] ?? action.replace(/_/g, ' ').toLowerCase()
}

export function AdminAudit() {
  const [page, setPage] = useState(0)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['audit', page],
    queryFn: () => listAuditLog(page * PAGE_SIZE, PAGE_SIZE),
  })

  const entries = data?.data ?? []
  const total = data?.total ?? 0

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Audit log</h1>

      {isLoading ? <SkeletonList count={10} /> :
       isError ? <ErrorState message="Could not load audit log." onRetry={() => refetch()} /> :
       entries.length === 0 ? <p className={styles.empty}>No audit events recorded yet.</p> : (
        <>
          <div className={styles.feed} aria-label="Audit activity log">
            {entries.map((entry) => (
              <div key={entry.id} className={styles.entry}>
                <div className={styles.entryTime}>
                  {new Date(entry.created_at).toLocaleString('en-IN', {
                    day: 'numeric', month: 'short', year: 'numeric',
                    hour: '2-digit', minute: '2-digit',
                  })}
                </div>
                <div className={styles.entryContent}>
                  <span className={styles.entryAction}>{humanAction(entry.action)}</span>
                  {entry.user_id && <span className={styles.entryActor}> by {entry.user_id}</span>}
                  {entry.entity_name && (
                    <span className={styles.entryResource}> · {entry.entity_name}</span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {total > PAGE_SIZE && (
            <div className={styles.pagination}>
              <button className={styles.pageBtn} disabled={page === 0} onClick={() => setPage((p) => p - 1)}>← Previous</button>
              <span className={styles.pageInfo}>{page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}</span>
              <button className={styles.pageBtn} disabled={(page + 1) * PAGE_SIZE >= total} onClick={() => setPage((p) => p + 1)}>Next →</button>
            </div>
          )}
        </>
       )}
    </div>
  )
}
