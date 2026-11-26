import { afterEach, describe, expect, it } from 'vitest'

import { orderedChannels, readPreferences, writePreferences } from './preferences'

describe('preferences', () => {
  afterEach(() => localStorage.clear())

  it('rend la valeur par défaut sans stockage ou avec une valeur inconnue', () => {
    expect(readPreferences().channel).toBe('whatsapp')
    localStorage.setItem('preferences', JSON.stringify({ channel: 'pigeon' }))
    expect(readPreferences().channel).toBe('whatsapp')
  })

  it('relit ce qui a été enregistré', () => {
    writePreferences({ channel: 'email' })
    expect(readPreferences().channel).toBe('email')
  })

  it('place le canal préféré en premier', () => {
    expect(orderedChannels('sms')).toEqual(['sms', 'whatsapp', 'email'])
  })
})
