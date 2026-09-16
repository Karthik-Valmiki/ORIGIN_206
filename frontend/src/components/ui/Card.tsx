import React from 'react'
import styles from './Card.module.css'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  clickable?: boolean
  padding?: 'sm' | 'md' | 'lg' | 'none'
  children: React.ReactNode
}

export function Card({ clickable, padding = 'md', children, className, onClick, ...props }: CardProps) {
  const Tag = clickable ? 'button' : 'div'
  return (
    <Tag
      className={[
        styles.card,
        clickable ? styles.clickable : '',
        styles[`pad_${padding}`],
        className ?? '',
      ]
        .filter(Boolean)
        .join(' ')}
      onClick={onClick as any}
      {...(clickable ? { type: 'button' } : {})}
      {...(props as any)}
    >
      {children}
    </Tag>
  )
}
