import { useRef, useState, useEffect } from 'react'
import { Camera, Trash2, RefreshCw } from 'lucide-react'
import styles from './ImageUploadGrid.module.css'

export type ImageSlotLabel = 'Front' | 'Back' | 'MRP / Batch' | 'Side'

const SLOT_LABELS: ImageSlotLabel[] = ['Front', 'Back', 'MRP / Batch', 'Side']
const MAX_IMAGES = 4
const MAX_SIZE_MB = 10

interface SlotFile {
  file: File
  objectUrl: string
  quality: 'ready' | 'low' | 'invalid'
}

interface ImageUploadGridProps {
  onChange: (files: File[]) => void
  error?: string
}

function validateFile(file: File): 'ready' | 'invalid' {
  if (!file.type.startsWith('image/')) return 'invalid'
  if (file.size > MAX_SIZE_MB * 1024 * 1024) return 'invalid'
  return 'ready'
}

const QUALITY_LABELS = {
  ready:   { text: '✓ Ready',       cls: 'qualityReady'   },
  low:     { text: '⚠ Low quality', cls: 'qualityLow'     },
  invalid: { text: '✕ Invalid',     cls: 'qualityInvalid' },
}

export function ImageUploadGrid({ onChange, error }: ImageUploadGridProps) {
  const [slots, setSlots] = useState<(SlotFile | null)[]>([null, null, null, null])
  const inputRefs = useRef<(HTMLInputElement | null)[]>([null, null, null, null])

  // Cleanup object URLs on unmount
  useEffect(() => {
    return () => {
      slots.forEach((s) => { if (s) URL.revokeObjectURL(s.objectUrl) })
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function updateSlot(idx: number, file: File | null) {
    setSlots((prev) => {
      const next = [...prev]
      if (prev[idx]?.objectUrl) URL.revokeObjectURL(prev[idx]!.objectUrl)
      if (file) {
        next[idx] = {
          file,
          objectUrl: URL.createObjectURL(file),
          quality: validateFile(file),
        }
      } else {
        next[idx] = null
      }
      const files = next.filter(Boolean).map((s) => s!.file)
      onChange(files)
      return next
    })
  }

  function handleFileChange(idx: number, e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) updateSlot(idx, file)
    e.target.value = '' // reset so same file can be re-selected
  }

  function handleDrop(idx: number, e: React.DragEvent) {
    e.preventDefault()
    const file = e.dataTransfer.files?.[0]
    if (file) updateSlot(idx, file)
  }

  function removeSlot(idx: number) {
    updateSlot(idx, null)
  }

  const filledCount = slots.filter(Boolean).length

  return (
    <div className={styles.container}>
      <div className={styles.grid}>
        {slots.map((slot, idx) => (
          <div
            key={idx}
            className={[styles.slot, slot ? styles.filled : styles.empty].join(' ')}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => handleDrop(idx, e)}
          >
            <input
              ref={(el) => { inputRefs.current[idx] = el }}
              type="file"
              accept="image/*"
              capture="environment"
              className={styles.fileInput}
              aria-label={`Upload ${SLOT_LABELS[idx]} image`}
              onChange={(e) => handleFileChange(idx, e)}
              id={`image-slot-${idx}`}
            />

            {slot ? (
              <div className={styles.preview}>
                <img
                  src={slot.objectUrl}
                  alt={`${SLOT_LABELS[idx]} preview`}
                  className={styles.thumb}
                />
                <div className={styles.previewOverlay}>
                  <span
                    className={[styles.quality, styles[QUALITY_LABELS[slot.quality].cls]].join(' ')}
                  >
                    {QUALITY_LABELS[slot.quality].text}
                  </span>
                  <div className={styles.previewActions}>
                    <button
                      type="button"
                      className={styles.iconBtn}
                      onClick={() => inputRefs.current[idx]?.click()}
                      aria-label={`Replace ${SLOT_LABELS[idx]} image`}
                      title="Replace"
                    >
                      <RefreshCw size={16} />
                    </button>
                    <button
                      type="button"
                      className={[styles.iconBtn, styles.removeBtn].join(' ')}
                      onClick={() => removeSlot(idx)}
                      aria-label={`Remove ${SLOT_LABELS[idx]} image`}
                      title="Remove"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
                <label htmlFor={`image-slot-${idx}`} className={styles.slotLabel}>
                  {SLOT_LABELS[idx]}
                </label>
              </div>
            ) : (
              <label htmlFor={`image-slot-${idx}`} className={styles.addArea}>
                <Camera size={24} className={styles.addIcon} aria-hidden="true" />
                <span className={styles.addLabel}>{SLOT_LABELS[idx]}</span>
                <span className={styles.addHint}>Tap to capture</span>
              </label>
            )}
          </div>
        ))}
      </div>

      <p className={styles.count}>
        {filledCount} of {MAX_IMAGES} images added
        {filledCount === 0 && ' — at least 1 required'}
      </p>

      {error && (
        <p className={styles.error} role="alert">{error}</p>
      )}
    </div>
  )
}
