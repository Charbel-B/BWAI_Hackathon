import { describe, expect, it } from 'vitest'

import type { ExtractedField } from '@/api/types'

import { segment } from './segments'

const field = (name: string, start: number, end: number): ExtractedField => ({
  name,
  status: 'FOUND',
  value: 'x',
  raw_text: 'x',
  confidence: 0.9,
  anchor: { kind: 'text', start, end, page: null, box: null },
  review: { state: 'PENDING', value: null, by: null, at: null },
  effective_value: 'x',
})

describe('segment', () => {
  it('découpe le texte autour des ancrages', () => {
    const parts = segment('Client : Akpro SARL', [field('customer.name', 9, 19)])
    expect(parts).toEqual([{ text: 'Client : ' }, { text: 'Akpro SARL', field: 'customer.name' }])
  })
  it('ignore un ancrage qui en chevauche un autre', () => {
    const parts = segment('abcdef', [field('a', 0, 4), field('b', 2, 6)])
    expect(parts.filter((p) => p.field)).toHaveLength(1)
  })
})
