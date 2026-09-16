// Admin Inspections — re-uses Officer History with admin-wide visibility
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { listInspections } from '../../api/inspections'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { SkeletonList } from '../../components/ui/Skeleton'
import { EmptyState, ErrorState } from '../../components/ui/EmptyState'
import styles from './Inspections.module.css'

const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'COMPLIANT', label: 'Compliant' },
  { value: 'NON_COMPLIANT', label: 'Non-compliant' },
  { value: 'REVIEW_REQUIRED', label: 'Review' },
  { value: 'PROCESSING_FAILED', label: 'Failed' },
  { value: 'PROCESSING', label: 'Processing' },
]

const PAGE_SIZE = 30

export function AdminInspections() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(0)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['inspections', 'admin', 'list', page],
    queryFn: () => listInspections(page * PAGE_SIZE, PAGE_SIZE),
  })

  const inspections = data?.data ?? []
  const total = data?.total ?? 0

  const filtered = inspections.filter((i) => {
    const matchSearch = !search ||
      i.inspection_number.toLowerCase().includes(search.toLowerCase()) ||
      (i.product_name ?? '').toLowerCase().includes(search.toLowerCase()) ||
      (i.officer_name ?? '').toLowerCase().includes(search.toLowerCase())
    const matchStatus = !statusFilter || i.status === statusFilter
    return matchSearch && matchStatus
  })

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>All inspections</h1>

      <div className={styles.filters}>
        <div className={styles.searchWrap}>
          <Search size={16} className={styles.searchIcon} />
          <input
            className={styles.searchInput}
            type="search"
            placeholder="Search by ID, product, officer…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search inspections"
            id="admin-search"
          />
        </div>
        <div className={styles.statusTabs} role="group">
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

      {isLoading ? <SkeletonList count={8} /> :
       isError ? <ErrorState message="Could not load inspections." onRetry={() => refetch()} /> :
       filtered.length === 0 ? <EmptyState title="No inspections found" description="Try adjusting filters." /> : (
        <>
          <div className={styles.table}>
            <div className={styles.thead}>
              <span>Inspection ID</span>
              <span>Product</span>
              <span>Officer</span>
              <span>Date</span>
              <span>Status</span>
            </div>
            {filtered.map((i) => (
              <button
                key={i.id}
                className={styles.trow}
                onClick={() => navigate(`/admin/inspections/${i.id}`)}
                aria-label={`Open inspection ${i.inspection_number}`}
              >
                <span className={styles.idCell}>{i.inspection_number}</span>
                <span className={styles.textCell}>{i.product_name ?? i.category_name ?? '—'}</span>
                <span className={styles.textCell}>{i.officer_name ?? '—'}</span>
                <span className={styles.dateCell}>
                  {new Date(i.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                </span>
                <span><StatusBadge status={i.status} size="sm" /></span>
              </button>
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
