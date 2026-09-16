import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Plus, Lock } from 'lucide-react'
import { listRules } from '../../api/rules'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { Button } from '../../components/ui/Button'
import { SkeletonList } from '../../components/ui/Skeleton'
import { EmptyState, ErrorState } from '../../components/ui/EmptyState'
import styles from './Rules.module.css'

export function AdminRules() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<'PUBLISHED' | 'DRAFT'>('PUBLISHED')

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['rules'],
    queryFn: listRules,
  })

  const rules = (data?.data ?? []).filter((r) =>
    tab === 'PUBLISHED' ? r.status === 'PUBLISHED' : r.status !== 'PUBLISHED',
  )

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Rule management</h1>
        <Button size="sm" onClick={() => navigate('/admin/rules/new')} id="btn-create-rule">
          <Plus size={16} />
          Create rule
        </Button>
      </div>

      {/* Lifecycle note */}
      <p className={styles.lifecycleNote}>
        Rule lifecycle: <strong>DRAFT</strong> → <strong>VALIDATED</strong> → <strong>PUBLISHED</strong> (immutable).
        Published rules cannot be edited — create a new version instead.
      </p>

      {/* Tabs */}
      <div className={styles.tabs} role="tablist">
        <button className={[styles.tab, tab === 'PUBLISHED' ? styles.activeTab : ''].filter(Boolean).join(' ')} onClick={() => setTab('PUBLISHED')} role="tab" aria-selected={tab === 'PUBLISHED'}>Published</button>
        <button className={[styles.tab, tab === 'DRAFT' ? styles.activeTab : ''].filter(Boolean).join(' ')} onClick={() => setTab('DRAFT')} role="tab" aria-selected={tab === 'DRAFT'}>Drafts</button>
      </div>

      {isLoading ? <SkeletonList count={5} /> :
       isError ? <ErrorState message="Could not load rules." onRetry={() => refetch()} /> :
       rules.length === 0 ? (
        <EmptyState
          title={tab === 'PUBLISHED' ? 'No published rules' : 'No draft rules'}
          description={tab === 'DRAFT' ? 'Create a new rule to get started.' : undefined}
          action={tab === 'DRAFT' ? { label: 'Create rule', onClick: () => navigate('/admin/rules/new') } : undefined}
        />
       ) : (
        <div className={styles.list}>
          {rules.map((rule) => (
            <div key={rule.id} className={styles.ruleRow}>
              <div className={styles.ruleMain}>
                <span className={styles.ruleName}>{rule.name}</span>
                <span className={styles.ruleMeta}>
                  {rule.category_name ?? 'All categories'} · v{rule.version}
                  {rule.effective_from ? ` · from ${new Date(rule.effective_from).toLocaleDateString('en-IN')}` : ''}
                </span>
              </div>
              <div className={styles.ruleActions}>
                <StatusBadge status={rule.status} size="sm" />
                {rule.status === 'PUBLISHED' ? (
                  <button
                    className={styles.newVersionBtn}
                    onClick={() => navigate(`/admin/rules/new?from=${rule.id}`)}
                    aria-label="Create new version"
                    title="Create new version (published rules are immutable)"
                  >
                    <Lock size={14} />
                    New version
                  </button>
                ) : (
                  <button
                    className={styles.editBtn}
                    onClick={() => navigate(`/admin/rules/${rule.id}`)}
                    aria-label={`Edit rule ${rule.name}`}
                  >
                    Edit
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
       )}
    </div>
  )
}
