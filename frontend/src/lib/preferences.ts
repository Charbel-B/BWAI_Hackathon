/**
 * Préférences propres à cet appareil (confort d'usage, jamais de donnée métier).
 * Le stockage peut être indisponible : la valeur par défaut s'applique alors.
 */
const KEY = 'preferences'
export const CHANNELS = ['whatsapp', 'sms', 'email'] as const
export type Channel = (typeof CHANNELS)[number]

export interface Preferences {
  channel: Channel
}

const DEFAULTS: Preferences = { channel: 'whatsapp' }

export function readPreferences(): Preferences {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw === null) return DEFAULTS
    const parsed = JSON.parse(raw) as Partial<Preferences>
    return {
      channel: CHANNELS.includes(parsed.channel as Channel)
        ? (parsed.channel as Channel)
        : DEFAULTS.channel,
    }
  } catch {
    return DEFAULTS
  }
}

export function writePreferences(next: Preferences): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    // Stockage indisponible : la préférence vaut pour la session en cours seulement.
  }
}

/** Canaux dans l'ordre d'affichage : le canal préféré d'abord. */
export function orderedChannels(preferred: Channel): Channel[] {
  return [preferred, ...CHANNELS.filter((c) => c !== preferred)]
}
