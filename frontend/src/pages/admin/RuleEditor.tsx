import { useState, useEffect, type FormEvent } from 'react'
import * as yaml from 'js-yaml'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft } from 'lucide-react'
import { getRule, createRule, validateRule, publishRule, type Rule } from '../../api/rules'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/ui/Input'
import { useToast } from '../../components/ui/Toast'
import { SkeletonList } from '../../components/ui/Skeleton'
import { listCategories } from '../../api/categories'
import styles from './RuleEditor.module.css'

export function AdminRuleEditor() {
  const { id } = useParams<{ id: string }>()
  const isNew = !id || id === 'new'
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { success, error: toastError, warning } = useToast()

  const [name, setName] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [effectiveFrom, setEffectiveFrom] = useState('')
  const [ruleYaml, setRuleYaml] = useState('clauses:\n  - rule_code: "LMPC-001"\n    check_type: "OCR_MATCH"\n    description: "Sample Rule"')
  const [yamlError, setYamlError] = useState('')
  const [validationResult, setValidationResult] = useState<{ valid: boolean; errors?: string[] } | null>(null)

  const { data: categories } = useQuery({ queryKey: ['categories'], queryFn: listCategories })
  const { data: existingRule, isLoading } = useQuery<Rule>({
    queryKey: ['rule', id],
    queryFn: () => getRule(id!),
    enabled: !isNew,
  })

  useEffect(() => {
    if (existingRule) {
      setName(existingRule.name)
      setCategoryId(existingRule.category_id ?? '')
      setEffectiveFrom(existingRule.effective_from?.slice(0, 10) ?? '')
      setRuleYaml(yaml.dump(existingRule.rule_data))
    }
  }, [existingRule])

  const isPublished = existingRule?.status === 'PUBLISHED'

  const saveMutation = useMutation({
    mutationFn: (payload: Partial<Rule>) => createRule(payload),
    onSuccess: () => {
      success('Rule saved as draft.')
      queryClient.invalidateQueries({ queryKey: ['rules'] })
      navigate('/admin/rules')
    },
    onError: () => toastError('Could not save rule.'),
  })

  const validateMutation = useMutation({
    mutationFn: validateRule,
    onSuccess: (result) => {
      setValidationResult(result)
      if (result.valid) success('Rule is valid.')
      else warning(`Validation found ${result.errors?.length ?? 0} issue(s).`)
    },
    onError: () => toastError('Validation request failed.'),
  })

  const publishMutation = useMutation({
    mutationFn: () => publishRule(id!),
    onSuccess: () => {
      success('Rule published successfully.')
      queryClient.invalidateQueries({ queryKey: ['rules'] })
      navigate('/admin/rules')
    },
    onError: () => toastError('Could not publish rule.'),
  })

  function parseYaml(): Record<string, unknown> | null {
    try {
      setYamlError('')
      const parsed = yaml.load(ruleYaml)
      if (typeof parsed !== 'object' || parsed === null) {
        throw new Error('YAML must represent an object')
      }
      return parsed as Record<string, unknown>
    } catch (e: any) {
      setYamlError('Invalid YAML — check syntax.')
      return null
    }
  }

  function handleSave(e: FormEvent) {
    e.preventDefault()
    const data = parseYaml()
    if (!data) return
    saveMutation.mutate({ name, category_id: categoryId || undefined, effective_from: effectiveFrom || undefined, rule_data: data })
  }

  function handleValidate() {
    const data = parseYaml()
    if (!data) return
    validateMutation.mutate({ name, category_id: categoryId || undefined, rule_data: data })
  }

  if (!isNew && isLoading) return <div style={{ padding: 'var(--space-6)' }}><SkeletonList count={4} /></div>

  return (
    <div className={styles.page}>
      <button className={styles.back} onClick={() => navigate('/admin/rules')}>
        <ChevronLeft size={18} /> Rules
      </button>

      <div className={styles.header}>
        <h1 className={styles.title}>{isNew ? 'Create rule' : `Edit rule${isPublished ? ' (read-only)' : ''}`}</h1>
        {isPublished && (
          <p className={styles.immutableNote}>
            This rule is published and immutable. To make changes, create a new version from the rules list.
          </p>
        )}
      </div>

      <form onSubmit={handleSave} className={styles.form} noValidate>
        <Input
          label="Rule name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          disabled={isPublished}
          id="rule-name"
        />

        <Select
          label="Category (leave empty for all)"
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          disabled={isPublished}
          id="rule-category"
        >
          <option value="">All categories</option>
          {categories?.map((c) => <option key={c.id} value={c.id}>{c.category_name}</option>)}
        </Select>

        <Input
          label="Effective from date"
          type="date"
          value={effectiveFrom}
          onChange={(e) => setEffectiveFrom(e.target.value)}
          disabled={isPublished}
          id="rule-effective-from"
        />

        {/* YAML editor */}
        <div className={styles.editorField}>
          <label className={styles.editorLabel} htmlFor="rule-yaml">
            Rule definition (YAML)
          </label>
          <textarea
            id="rule-yaml"
            className={[styles.jsonEditor, yamlError ? styles.hasError : ''].filter(Boolean).join(' ')}
            value={ruleYaml}
            onChange={(e) => { setRuleYaml(e.target.value); setYamlError(''); setValidationResult(null) }}
            rows={18}
            spellCheck={false}
            disabled={isPublished}
            aria-describedby={yamlError ? 'yaml-error' : undefined}
          />
          {yamlError && <p id="yaml-error" className={styles.jsonError} role="alert">{yamlError}</p>}
        </div>

        {/* Validation result */}
        {validationResult && (
          <div className={[styles.validationResult, validationResult.valid ? styles.valid : styles.invalid].join(' ')} role="status">
            {validationResult.valid ? '✓ Rule is valid' : (
              <>
                <p>✕ Validation failed:</p>
                <ul>{validationResult.errors?.map((e, i) => <li key={i}>{e}</li>)}</ul>
              </>
            )}
          </div>
        )}

        {!isPublished && (
          <div className={styles.actions}>
            <Button type="button" variant="secondary" onClick={handleValidate} loading={validateMutation.isPending} id="btn-validate-rule">
              Validate
            </Button>
            <Button type="submit" loading={saveMutation.isPending} id="btn-save-rule">
              Save draft
            </Button>
            {!isNew && existingRule?.status === 'VALIDATED' && (
              <Button
                type="button"
                variant="secondary"
                onClick={() => publishMutation.mutate()}
                loading={publishMutation.isPending}
                id="btn-publish-rule"
              >
                Publish
              </Button>
            )}
          </div>
        )}
      </form>
    </div>
  )
}
