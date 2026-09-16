import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { listInspections } from '../../api/inspections'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { SkeletonList } from '../../components/ui/Skeleton'
import { EmptyState, ErrorState } from '../../components/ui/EmptyState'
import styles from './History.module.css'

const STATUS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: '', label: 'All' },
  { value: 'COMPLIANT', label: 'Compliant' },
  { value: 'NON_COMPLIANT', label: 'Non-compliant' },
  { value: 'REVIEW_REQUIRED', label: 'Review required' },
  { value: 'PROCESSING_FAILED', label: 'Failed' },
  { value: 'PROCESSING', label: 'Processing' },
]

const PAGE_SIZE = 20

export function OfficerHistory() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(0)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['inspections', 'officer', 'history', page],
    queryFn: () => listInspections(page * PAGE_SIZE, PAGE_SIZE),
  })

  const inspections = data?.data ?? []
  const total = data?.total ?? 0

  // Client-side filter by search/status (for current page data)
  const filtered = inspections.filter((i) => {
    const matchSearch =
      !search ||
      i.inspection_number.toLowerCase().includes(search.toLowerCase()) ||
      (i.product_name ?? '').toLowerCase().includes(search.toLowerCase()) ||
      (i.category_name ?? '').toLowerCase().includes(search.toLowerCase())
    const matchStatus = !statusFilter || i.status === statusFilter
    return matchSearch && matchStatus
  })

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Inspection history</h1>

      {/* Filters */}
      <div className={styles.filters}>
        <div className={styles.searchWrap}>
          <Search size={16} className={styles.searchIcon} aria-hidden="true" />
          <input
            type="search"
            placeholder="Search inspections…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className={styles.searchInput}
            aria-label="Search inspections"
            id="history-search"
          />
        </div>
        <div className={styles.statusTabs} role="group" aria-label="Filter by status">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className={[styles.statusTab, statusFilter === opt.value ? styles.activeTab : ''].filter(Boolean).join(' ')}
              onClick={() => { setStatusFilter(opt.value); setPage(0) }}
              aria-pressed={statusFilter === opt.value}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      {isLoading ? (
        <SkeletonList count={6} />
      ) : isError ? (
        <ErrorState message="Could not load inspection history." onRetry={() => refetch()} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No inspections found"
          description={search || statusFilter ? 'Try adjusting your filters.' : 'Start your first product inspection.'}
          action={!search && !statusFilter ? { label: 'Start inspection', onClick: () => navigate('/officer/inspect') } : undefined}
        />
      ) : (
        <>
          <div className={styles.list}>
            {filtered.map((i) => (
              <button
                key={i.id}
                className={styles.row}
                onClick={() => navigate(`/officer/inspect/${i.id}/result`)}
                aria-label={`Inspection ${i.inspection_number}`}
              >
                <div className={styles.rowMain}>
                  <span className={styles.rowId}>{i.inspection_number}</span>
                  <span className={styles.rowCategory}>{i.category_name ?? '—'}</span>
                </div>
                <div className={styles.rowMeta}>
                  <span className={styles.rowDate}>
                    {new Date(i.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                  </span>
                  <StatusBadge status={i.status} size="sm" />
                </div>
              </button>
            ))}
          </div>

          {/* Pagination */}
          {total > PAGE_SIZE && (
            <div className={styles.pagination}>
              <button
                className={styles.pageBtn}
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
                aria-label="Previous page"
              >
                ← Previous
              </button>
              <span className={styles.pageInfo}>
                {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
              </span>
              <button
                className={styles.pageBtn}
                disabled={(page + 1) * PAGE_SIZE >= total}
                onClick={() => setPage((p) => p + 1)}
                aria-label="Next page"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
