import type { User } from '@/api/types'

/**
 * Session de l'onglet. Conservée en sessionStorage pour survivre à un rechargement pendant la
 * démonstration ; perdue à la fermeture de l'onglet. Le stockage peut être indisponible
 * (navigation privée) : la session reste alors en mémoire.
 */
const KEY = 'session'

interface Stored {
  token: string
  user: User
}

type Listener = () => void

function read(): Stored | null {
  try {
    const raw = sessionStorage.getItem(KEY)
    return raw === null ? null : (JSON.parse(raw) as Stored)
  } catch {
    return null
  }
}

let current: Stored | null = read()
const listeners = new Set<Listener>()

function publish(next: Stored | null): void {
  current = next
  try {
    if (next === null) sessionStorage.removeItem(KEY)
    else sessionStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    // Stockage indisponible : la session vit en mémoire seulement.
  }
  listeners.forEach((listener) => listener())
}

export const session = {
  token: (): string | null => current?.token ?? null,
  user: (): User | null => current?.user ?? null,
  open: (token: string, user: User): void => publish({ token, user }),
  clear: (): void => publish(null),
  subscribe(listener: Listener): () => void {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
}
