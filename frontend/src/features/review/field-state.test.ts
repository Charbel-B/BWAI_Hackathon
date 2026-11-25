import { describe, expect, it } from 'vitest'

import type { Anomaly, ExtractedField } from '@/api/types'

import { fieldLabel, fieldState } from './field-state'

const base: ExtractedField = {
  name: 'lines[0].quantity',
  status: 'FOUND',
  value: '20',
  raw_text: '20',
  confidence: 0.72,
  anchor: null,
  review: { state: 'PENDING', value: null, by: null, at: null },
  effective_value: '20',
}
const low: Anomaly = {
  id: 'LOW_CONFIDENCE:lines[0].quantity',
  code: 'LOW_CONFIDENCE',
  severity: 'BLOCKING',
  field: 'lines[0].quantity',
  message: '',
  resolved: false,
  resolved_by: null,
  justification: null,
}

describe('fieldState', () => {
  it('suit l’anomalie du backend pour l’incertitude', () => {
    expect(fieldState(base, [low])).toBe('unsure')
    expect(fieldState(base, [])).toBe('sure')
  })
  it('distingue absent, corrigé et confirmé', () => {
    const empty = {
      ...base,
      status: 'MISSING',
      value: null,
      effective_value: null,
      confidence: null,
    }
    const required = { ...low, code: 'MISSING_REQUIRED_FIELD' }
    expect(fieldState(empty, [required])).toBe('missing')
    expect(fieldState(empty, [])).toBe('absent')
    expect(
      fieldState({ ...base, review: { state: 'CORRECTED', value: '40', by: 'u', at: 'x' } }, [low]),
    ).toBe('corrected')
    expect(
      fieldState({ ...base, review: { state: 'CONFIRMED', value: null, by: 'u', at: 'x' } }, [low]),
    ).toBe('confirmed')
  })
})

describe('fieldLabel', () => {
  it('nomme les champs de ligne avec leur numéro humain', () => {
    expect(fieldLabel('lines[1].unit_price')).toEqual({ label: 'Prix unitaire', line: 2 })
    expect(fieldLabel('customer.name')).toEqual({ label: 'Client', line: null })
  })
})
