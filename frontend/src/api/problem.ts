/** Erreur renvoyée par l'API au format problem+json (docs/contrats/api.md). */
export interface ProblemAnomaly {
  id: string
  code: string
  message: string
}

export class ApiProblem extends Error {
  readonly code: string
  readonly status: number
  readonly anomalies: readonly ProblemAnomaly[]

  constructor(status: number, code: string, detail: string, anomalies: ProblemAnomaly[] = []) {
    super(detail)
    this.status = status
    this.code = code
    this.anomalies = anomalies
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

/** Transforme le corps d'erreur, quel qu'il soit, en ApiProblem. */
export function toProblem(error: unknown, status: number): ApiProblem {
  if (isRecord(error) && typeof error['code'] === 'string') {
    const anomalies = Array.isArray(error['anomalies'])
      ? (error['anomalies'] as ProblemAnomaly[])
      : []
    const detail = typeof error['detail'] === 'string' ? error['detail'] : error['code']
    return new ApiProblem(status, error['code'], detail, anomalies)
  }
  return new ApiProblem(status, 'UNKNOWN', 'Réponse inattendue du serveur')
}

/** Rend les données d'un appel openapi-fetch, ou lève l'ApiProblem correspondant. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined || result.data === undefined) {
    throw toProblem(result.error, result.response.status)
  }
  return result.data
}
