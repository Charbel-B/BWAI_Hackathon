import { describe, expect, it } from 'vitest'

import { formatAmount, percent } from './format'

describe('formatAmount', () => {
  it('regroupe les milliers sans flottant', () => {
    expect(formatAmount('180540')).toBe('180 540')
    expect(formatAmount('1284300')).toBe('1 284 300')
  })
  it('garde les décimales utiles et retire les zéros inutiles', () => {
    expect(formatAmount('2.50')).toBe('2,50')
    expect(formatAmount('12.00')).toBe('12')
  })
  it('affiche le signe moins typographique', () => {
    expect(formatAmount('-500')).toBe('−500')
  })
})

describe('percent', () => {
  it('arrondit la confiance', () => {
    expect(percent(0.954)).toBe('95 %')
  })
})
