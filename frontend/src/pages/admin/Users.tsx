import { useState, type FormEvent } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, UserCheck, UserX } from 'lucide-react'
import { listUsers, createUser, activateUser, deactivateUser, type CreateUserPayload } from '../../api/users'
import { Button } from '../../components/ui/Button'
import { Modal } from '../../components/ui/Modal'
import { Input, Select } from '../../components/ui/Input'
import { SkeletonList } from '../../components/ui/Skeleton'
import { EmptyState, ErrorState } from '../../components/ui/EmptyState'
import { useToast } from '../../components/ui/Toast'
import styles from './Users.module.css'

export function AdminUsers() {
  const queryClient = useQueryClient()
  const { success, error: toastError } = useToast()
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<CreateUserPayload>({ full_name: '', email: '', password: '', roles: ['OFFICER'] })
  const [formError, setFormError] = useState('')

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['users'],
    queryFn: () => listUsers(),
  })

  const users = (data ?? []).filter((u) =>
    !search || u.full_name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase())
  )

  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => { success('Officer account created.'); queryClient.invalidateQueries({ queryKey: ['users'] }); setShowCreate(false); setForm({ full_name: '', email: '', password: '', roles: ['OFFICER'] }) },
    onError: () => toastError('Could not create user.'),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => active ? deactivateUser(id) : activateUser(id),
    onSuccess: (_, { active }) => { success(active ? 'User deactivated.' : 'User activated.'); queryClient.invalidateQueries({ queryKey: ['users'] }) },
    onError: () => toastError('Could not update user status.'),
  })

  function handleCreate(e: FormEvent) {
    e.preventDefault()
    if (!form.full_name || !form.email || !form.password) { setFormError('All fields are required.'); return }
    setFormError('')
    createMutation.mutate(form)
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Users</h1>
        <Button size="sm" onClick={() => setShowCreate(true)} id="btn-create-user">
          <Plus size={16} /> Create officer
        </Button>
      </div>

      <div className={styles.searchWrap}>
        <input className={styles.searchInput} type="search" placeholder="Search users…" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search users" id="user-search" />
      </div>

      {isLoading ? <SkeletonList count={5} /> :
       isError ? <ErrorState message="Could not load users." onRetry={() => refetch()} /> :
       users.length === 0 ? <EmptyState title="No users found" /> : (
        <div className={styles.list}>
          {users.map((u) => (
            <div key={u.id} className={styles.row}>
              <div className={styles.avatar}>{u.full_name[0]?.toUpperCase()}</div>
              <div className={styles.userInfo}>
                <span className={styles.userName}>{u.full_name}</span>
                <span className={styles.userEmail}>{u.email}</span>
                <span className={styles.userRole}>{u.roles.join(', ')}</span>
              </div>
              <div className={styles.rowActions}>
                <span className={[styles.statusDot, u.is_active ? styles.active : styles.inactive].join(' ')} aria-label={u.is_active ? 'Active' : 'Inactive'} />
                <button
                  className={styles.toggleBtn}
                  onClick={() => toggleMutation.mutate({ id: u.id, active: u.is_active })}
                  aria-label={u.is_active ? 'Deactivate user' : 'Activate user'}
                  title={u.is_active ? 'Deactivate' : 'Activate'}
                >
                  {u.is_active ? <UserX size={18} /> : <UserCheck size={18} />}
                </button>
              </div>
            </div>
          ))}
        </div>
       )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create officer account" size="sm">
        <form onSubmit={handleCreate} className={styles.createForm} noValidate>
          <Input label="Full name" value={form.full_name} onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))} required id="new-user-name" />
          <Input label="Email address" type="email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} required id="new-user-email" />
          <Input label="Initial password" type="password" value={form.password} onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))} required id="new-user-password" hint="User should change this after first login." />
          <Select label="Role" value={form.roles[0]} onChange={(e) => setForm((f) => ({ ...f, roles: [e.target.value] }))} id="new-user-role">
            <option value="OFFICER">Officer</option>
            <option value="ADMIN">Admin</option>
          </Select>
          {formError && <p className={styles.formError} role="alert">{formError}</p>}
          <Button type="submit" fullWidth loading={createMutation.isPending} id="btn-submit-create-user">Create account</Button>
        </form>
      </Modal>
    </div>
  )
}
