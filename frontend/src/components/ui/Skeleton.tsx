import styles from './Skeleton.module.css'

interface SkeletonProps {
  width?: string
  height?: string
  className?: string
  rounded?: boolean
}

export function Skeleton({ width, height = '1em', className, rounded }: SkeletonProps) {
  return (
    <span
      className={[styles.skeleton, rounded ? styles.rounded : '', className ?? ''].filter(Boolean).join(' ')}
      style={{ width, height }}
      aria-hidden="true"
    />
  )
}

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className={styles.card}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} width={i === 0 ? '60%' : i % 2 === 0 ? '80%' : '40%'} />
      ))}
    </div>
  )
}

export function SkeletonList({ count = 5 }: { count?: number }) {
  return (
    <div className={styles.list}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}
