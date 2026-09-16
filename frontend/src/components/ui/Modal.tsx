import React, { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import styles from './Modal.module.css'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  size?: 'sm' | 'md' | 'lg'
}

export function Modal({ open, onClose, title, children, size = 'md' }: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const el = dialogRef.current
    if (!el) return
    if (open) {
      el.showModal()
    } else {
      el.close()
    }
  }, [open])

  useEffect(() => {
    const el = dialogRef.current
    if (!el) return
    const handler = () => onClose()
    el.addEventListener('close', handler)
    return () => el.removeEventListener('close', handler)
  }, [onClose])

  if (!open) return null

  return createPortal(
    <dialog
      ref={dialogRef}
      className={[styles.dialog, styles[size]].join(' ')}
      aria-labelledby="modal-title"
      onClick={(e) => { if (e.target === dialogRef.current) onClose() }}
    >
      <div className={styles.header}>
        <h2 id="modal-title" className={styles.title}>{title}</h2>
        <button className={styles.closeBtn} onClick={onClose} aria-label="Close">
          <X size={20} />
        </button>
      </div>
      <div className={styles.body}>{children}</div>
    </dialog>,
    document.body,
  )
}
