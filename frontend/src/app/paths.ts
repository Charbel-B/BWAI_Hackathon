/** Chemins de l'application, définis une seule fois. */
export const paths = {
  landing: '/',
  login: '/connexion',
  dashboard: '/tableau',
  import: '/importer',
  invoice: (id: string) => `/factures/${id}`,
  invoicePattern: '/factures/:invoiceId',
  audit: '/journal',
  settings: '/parametres',
  verify: (id: string, code: string) => `/verifier/${id}?code=${code}`,
  verifyPattern: '/verifier/:invoiceId',
} as const
