import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { ChevronLeft } from 'lucide-react'
import { listCategories } from '../../api/categories'
import { createInspection } from '../../api/inspections'
import { ImageUploadGrid } from '../../components/inspection/ImageUploadGrid'
import { Button } from '../../components/ui/Button'
import { Select, Input, Textarea } from '../../components/ui/Input'
import { useToast } from '../../components/ui/Toast'
import styles from './NewInspection.module.css'

export function NewInspection() {
  const navigate = useNavigate()
  const { error: toastError } = useToast()

  const [images, setImages] = useState<File[]>([])
  const [categoryId, setCategoryId] = useState('')
  const [productName, setProductName] = useState('')
  const [location, setLocation] = useState('')
  const [isImported, setIsImported] = useState(false)
  const [notes, setNotes] = useState('')
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})

  const { data: categories, isLoading: catsLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: listCategories,
  })

  const mutation = useMutation({
    mutationFn: createInspection,
    onSuccess: (data) => {
      navigate(`/officer/inspect/${data.id}/processing`)
    },
    onError: () => {
      toastError("We couldn't submit this inspection. Please try again.")
    },
  })

  function validate(): boolean {
    const errs: Record<string, string> = {}
    if (!categoryId) errs.category = 'Select a product category'
    if (images.length === 0) errs.images = 'Add at least one image'
    if (images.length > 4) errs.images = 'Maximum 4 images allowed'
    setFormErrors(errs)
    return Object.keys(errs).length === 0
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!validate()) return
    mutation.mutate({ category_id: categoryId, product_name: productName || undefined, location: location || undefined, is_imported: isImported, notes: notes || undefined, images })
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <button className={styles.back} onClick={() => navigate(-1)} aria-label="Go back">
          <ChevronLeft size={20} />
        </button>
        <h1 className={styles.title}>New Inspection</h1>
      </header>

      <form onSubmit={handleSubmit} className={styles.form} noValidate>
        {/* Images — first, most important */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Product images</h2>
          <p className={styles.sectionHint}>
            Photograph all sides of the label clearly. Capture front, back, MRP/batch stamp, and side panel.
          </p>
          <ImageUploadGrid onChange={setImages} error={formErrors.images} />
        </section>

        {/* Product details */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Product details</h2>

          <Select
            label="Product category"
            required
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
            error={formErrors.category}
            id="select-category"
          >
            <option value="">Select category…</option>
            {catsLoading && <option disabled>Loading…</option>}
            {categories?.map((c) => (
              <option key={c.id} value={c.id}>{c.category_name}</option>
            ))}
          </Select>

          <Input
            label="Product name"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
            placeholder="e.g. Sunrise Atta 5 kg"
            id="input-product-name"
          />

          <Input
            label="Inspection location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Shop no. 12, Gandhi Bazaar"
            id="input-location"
          />

          <div className={styles.checkRow}>
            <input
              type="checkbox"
              id="chk-imported"
              checked={isImported}
              onChange={(e) => setIsImported(e.target.checked)}
              className={styles.checkbox}
            />
            <label htmlFor="chk-imported" className={styles.checkLabel}>
              Imported product
            </label>
          </div>

          <Textarea
            label="Notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Any observations or context…"
            id="input-notes"
          />
        </section>

        <div className={styles.actions}>
          <Button
            type="submit"
            size="lg"
            fullWidth
            loading={mutation.isPending}
            id="btn-submit-inspection"
          >
            Submit for verification
          </Button>
          <Button
            type="button"
            variant="ghost"
            fullWidth
            onClick={() => navigate(-1)}
          >
            Cancel
          </Button>
        </div>
      </form>
    </div>
  )
}
