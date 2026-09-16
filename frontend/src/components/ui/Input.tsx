import React, { useId } from 'react'
import styles from './Input.module.css'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
  hint?: string
}

export function Input({ label, error, hint, id: propId, className, ...props }: InputProps) {
  const generatedId = useId()
  const id = propId ?? generatedId

  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>
        {label}
        {props.required && <span aria-hidden="true" className={styles.required}> *</span>}
      </label>
      <input
        id={id}
        className={[styles.input, error ? styles.hasError : '', className ?? ''].filter(Boolean).join(' ')}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
        aria-invalid={!!error}
        {...props}
      />
      {hint && !error && <p id={`${id}-hint`} className={styles.hint}>{hint}</p>}
      {error && (
        <p id={`${id}-error`} className={styles.error} role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label: string
  error?: string
  hint?: string
  children: React.ReactNode
}

export function Select({ label, error, hint, id: propId, children, className, ...props }: SelectProps) {
  const generatedId = useId()
  const id = propId ?? generatedId

  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>
        {label}
        {props.required && <span aria-hidden="true" className={styles.required}> *</span>}
      </label>
      <select
        id={id}
        className={[styles.select, error ? styles.hasError : '', className ?? ''].filter(Boolean).join(' ')}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
        aria-invalid={!!error}
        {...props}
      >
        {children}
      </select>
      {hint && !error && <p id={`${id}-hint`} className={styles.hint}>{hint}</p>}
      {error && (
        <p id={`${id}-error`} className={styles.error} role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string
  error?: string
  hint?: string
}

export function Textarea({ label, error, hint, id: propId, className, ...props }: TextareaProps) {
  const generatedId = useId()
  const id = propId ?? generatedId

  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>{label}</label>
      <textarea
        id={id}
        className={[styles.input, error ? styles.hasError : '', className ?? ''].filter(Boolean).join(' ')}
        rows={3}
        {...props}
      />
      {error && <p className={styles.error} role="alert">{error}</p>}
      {hint && !error && <p className={styles.hint}>{hint}</p>}
    </div>
  )
}
