import { useState, useRef, useEffect, useCallback } from 'react'
import { ZoomIn, ZoomOut, ChevronLeft, ChevronRight } from 'lucide-react'
import type { InspectionImage, Finding } from '../../api/inspections'
import styles from './EvidenceViewer.module.css'

interface EvidenceViewerProps {
  images: InspectionImage[]
  findings: Finding[]
  highlightedFinding?: string | null
  onRegionClick?: (findingId: string) => void
  apiBase?: string
}

export function EvidenceViewer({ images, findings, highlightedFinding, onRegionClick, apiBase = '' }: EvidenceViewerProps) {
  const [activeIdx, setActiveIdx] = useState(0)
  const [zoom, setZoom] = useState(1)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const imgRef = useRef<HTMLImageElement | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const activeImage = images[activeIdx]
  const imageSrc = activeImage
    ? `${apiBase}/api/v1/images/${activeImage.id}/file`
    : null

  // Findings with bounding boxes for active image
  const activeFindingsForImage = findings.filter(
    (f) => f.details?.evidence?.image_id === activeImage?.id && f.details?.evidence?.bounding_box,
  )

  const drawOverlays = useCallback(() => {
    const canvas = canvasRef.current
    const img = imgRef.current
    if (!canvas || !img || img.naturalWidth === 0) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    canvas.width = img.naturalWidth
    canvas.height = img.naturalHeight
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    activeFindingsForImage.forEach((f) => {
      const bb = f.details!.evidence!.bounding_box!
      const [x, y, w, h] = bb
      const isHighlighted = f.details?.clause_id === highlightedFinding

      ctx.strokeStyle = isHighlighted ? '#2563eb' : 'rgba(100,100,200,0.7)'
      ctx.lineWidth = isHighlighted ? 3 : 2
      ctx.strokeRect(x, y, w, h)

      if (isHighlighted) {
        ctx.fillStyle = 'rgba(37, 99, 235, 0.12)'
        ctx.fillRect(x, y, w, h)
      }
    })
  }, [activeFindingsForImage, highlightedFinding])

  useEffect(() => {
    drawOverlays()
  }, [drawOverlays, activeIdx, zoom])

  function handleImgLoad(e: React.SyntheticEvent<HTMLImageElement>) {
    imgRef.current = e.currentTarget
    drawOverlays()
  }

  function handleCanvasClick(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!onRegionClick || !imgRef.current) return
    const canvas = canvasRef.current!
    const rect = canvas.getBoundingClientRect()
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    const cx = (e.clientX - rect.left) * scaleX
    const cy = (e.clientY - rect.top) * scaleY

    for (const f of activeFindingsForImage) {
      const [x, y, w, h] = f.details!.evidence!.bounding_box!
      if (cx >= x && cx <= x + w && cy >= y && cy <= y + h) {
        if (f.details?.clause_id) onRegionClick(f.details.clause_id)
        break
      }
    }
  }

  if (!images.length) return null

  return (
    <div className={styles.viewer}>
      {/* Image display */}
      <div className={styles.imageArea} ref={containerRef}>
        {imageSrc ? (
          <div className={styles.imageWrap} style={{ transform: `scale(${zoom})` }}>
            <img
              src={imageSrc}
              alt={`Package image ${activeIdx + 1}`}
              className={styles.image}
              onLoad={handleImgLoad}
              draggable={false}
            />
            <canvas
              ref={canvasRef}
              className={styles.overlayCanvas}
              onClick={handleCanvasClick}
              aria-label="OCR evidence regions"
            />
          </div>
        ) : (
          <div className={styles.noImage}>No image</div>
        )}

        {/* Zoom controls */}
        <div className={styles.zoomControls}>
          <button
            className={styles.zoomBtn}
            onClick={() => setZoom((z) => Math.min(3, z + 0.25))}
            aria-label="Zoom in"
            disabled={zoom >= 3}
          >
            <ZoomIn size={18} />
          </button>
          <span className={styles.zoomLabel}>{Math.round(zoom * 100)}%</span>
          <button
            className={styles.zoomBtn}
            onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}
            aria-label="Zoom out"
            disabled={zoom <= 0.5}
          >
            <ZoomOut size={18} />
          </button>
        </div>
      </div>

      {/* Image strip */}
      {images.length > 1 && (
        <div className={styles.strip}>
          <button
            className={styles.stripNav}
            onClick={() => setActiveIdx((i) => Math.max(0, i - 1))}
            disabled={activeIdx === 0}
            aria-label="Previous image"
          >
            <ChevronLeft size={18} />
          </button>
          {images.map((img, idx) => (
            <button
              key={img.id}
              className={[styles.thumb, idx === activeIdx ? styles.activeThumb : ''].filter(Boolean).join(' ')}
              onClick={() => { setActiveIdx(idx); setZoom(1) }}
              aria-label={`Image ${idx + 1}`}
              aria-pressed={idx === activeIdx}
            >
              <img
                src={`${apiBase}/api/v1/images/${img.id}/file`}
                alt={`Thumbnail ${idx + 1}`}
                className={styles.thumbImg}
              />
            </button>
          ))}
          <button
            className={styles.stripNav}
            onClick={() => setActiveIdx((i) => Math.min(images.length - 1, i + 1))}
            disabled={activeIdx === images.length - 1}
            aria-label="Next image"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      )}
    </div>
  )
}
