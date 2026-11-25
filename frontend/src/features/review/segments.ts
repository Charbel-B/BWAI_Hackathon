import type { ExtractedField } from '@/api/types'

interface Segment {
  text: string
  field?: string
}

/** Découpe le texte selon les ancrages des champs ; un ancrage qui en chevauche un autre est ignoré. */
export function segment(text: string, fields: readonly ExtractedField[]): Segment[] {
  const anchors = fields
    .flatMap((f) =>
      f.anchor?.kind === 'text' && f.anchor.start != null && f.anchor.end != null
        ? [{ start: f.anchor.start, end: f.anchor.end, field: f.name }]
        : [],
    )
    .filter((a) => a.end > a.start && a.end <= text.length)
    .sort((a, b) => a.start - b.start)
  const out: Segment[] = []
  let cursor = 0
  for (const anchor of anchors) {
    if (anchor.start < cursor) continue
    if (anchor.start > cursor) out.push({ text: text.slice(cursor, anchor.start) })
    out.push({ text: text.slice(anchor.start, anchor.end), field: anchor.field })
    cursor = anchor.end
  }
  if (cursor < text.length) out.push({ text: text.slice(cursor) })
  return out
}
