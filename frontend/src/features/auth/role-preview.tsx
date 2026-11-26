import { Check, ShieldCheck } from 'lucide-react'
import { type CSSProperties, useEffect, useState } from 'react'

import padlockImage from '@/assets/cadenas-verre.webp'
import { ConfidenceRing } from '@/components/confidence-ring'
import { fr } from '@/i18n/fr'
import { percent } from '@/lib/format'

import { type DemoRole, ROLES } from './demo-roles'

const p = fr.login.preview
const CYCLE_MS = 5200
const order = (i: number) => ({ '--i': i }) as CSSProperties
const card = 'glass rounded-[20px] text-ink shadow-float'

function OperatorScene() {
  return (
    <div className="grid gap-3">
      <p
        style={order(0)}
        className="enter max-w-[340px] rounded-[20px] rounded-tl-md bg-whatsapp-wash px-4 py-3 text-[14px] leading-relaxed text-whatsapp-ink shadow-float"
      >
        {p.operateur.message}
      </p>
      <ul className="ml-auto grid w-full max-w-[360px] gap-2">
        {p.operateur.fields.map((f, i) => {
          const unsure = f.confidence < 0.85
          return (
            <li
              key={f.label}
              style={order(i + 2)}
              className={`enter-pop ${card} grid grid-cols-[28px_1fr_auto] items-center gap-3 px-4 py-3 ${unsure ? 'outline-[1.5px] -outline-offset-[1.5px] outline-amber outline-dashed' : ''}`}
            >
              <ConfidenceRing value={f.confidence} tone={unsure ? 'amber' : 'sky'} />
              <span className="min-w-0">
                <span className="label block text-ink-soft">{f.label}</span>
                <b className="block truncate font-medium">{f.value}</b>
              </span>
              <span
                className={`rounded-full px-2.5 py-1 font-mono text-[11px] ${unsure ? 'bg-amber text-amber-deep' : 'bg-sky-wash text-sky-deep'}`}
              >
                {percent(f.confidence)}
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function ValidatorScene() {
  return (
    <div className="relative grid gap-3">
      <div style={order(0)} className={`enter ${card} grid gap-3 p-5`}>
        <span className="label text-ink-soft">{p.validateur.draft}</span>
        <span className="flex items-center gap-2 text-sm font-medium text-sky-deep">
          <span className="grid size-6 place-items-center rounded-full bg-sky text-white">
            <Check className="size-3.5" strokeWidth={3} aria-hidden="true" />
          </span>
          {p.validateur.clean}
        </span>
        <div className="space-y-2 pt-1" aria-hidden="true">
          <div className="h-2 w-4/5 rounded-full bg-ink/10" />
          <div className="h-2 w-3/5 rounded-full bg-ink/10" />
          <div className="h-2 w-2/3 rounded-full bg-ink/10" />
        </div>
      </div>
      <div
        style={order(1)}
        className="stamp mx-auto -mt-2 grid place-items-center rounded-[18px] border-[3px] border-lime bg-night/90 px-6 py-3 text-white shadow-float"
      >
        <span className="tabular text-[30px] tracking-[-0.02em]">{p.validateur.number}</span>
      </div>
      <p style={order(3)} className="enter text-center text-[13px] text-white/85">
        {p.validateur.rule}
      </p>
    </div>
  )
}

function AdminScene() {
  return (
    <ol className="mx-auto grid w-full max-w-[380px]">
      {p.admin.blocks.map((b, i) => (
        <li key={b.seq} className="grid">
          {i > 0 && (
            <span
              aria-hidden="true"
              style={order(i)}
              className="chain-link mx-auto h-4 w-0.5 rounded-full bg-lime"
            />
          )}
          <div
            style={order(i)}
            className={`enter-pop ${card} grid grid-cols-[auto_1fr_auto] items-center gap-3 px-4 py-2.5`}
          >
            <span className="tabular text-xs text-sky-deep">{b.seq}</span>
            <span className="text-sm font-medium">{b.action}</span>
            <span className="font-mono text-[11px] text-ink-soft">{b.hash}</span>
          </div>
        </li>
      ))}
      <li style={order(5)} className="enter-pop mt-3 flex justify-center">
        <span className="inline-flex items-center gap-2 rounded-full bg-night px-4 py-2 text-sm font-medium text-white shadow-float">
          <ShieldCheck className="size-4 text-lime" aria-hidden="true" />
          {p.admin.intact}
        </span>
      </li>
    </ol>
  )
}

const SCENES = { operateur: OperatorScene, validateur: ValidatorScene, admin: AdminScene } as const

function reducedMotion(): boolean {
  return (
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

/**
 * Ce qui attend chaque rôle, joué en petites scènes. Défile seul ; se cale sur le compte choisi.
 */
export function RolePreview({ selected }: { selected: DemoRole | null }) {
  const [cycled, setCycled] = useState<DemoRole>('operateur')
  const role = selected ?? cycled

  useEffect(() => {
    if (selected !== null || reducedMotion()) return
    const timer = window.setInterval(
      () => setCycled((r) => ROLES[(ROLES.indexOf(r) + 1) % ROLES.length] ?? 'operateur'),
      CYCLE_MS,
    )
    return () => window.clearInterval(timer)
  }, [selected])

  const Scene = SCENES[role]
  return (
    <div className="flex h-full flex-col">
      <div className="mx-auto mt-5 flex w-full max-w-[520px] gap-1.5" aria-hidden="true">
        {ROLES.map((r) => (
          <span
            key={r}
            className={`h-1 flex-1 rounded-full transition-colors duration-500 ${r === role ? 'bg-white' : 'bg-white/25'}`}
          />
        ))}
      </div>
      <div key={role} className="mx-auto my-auto grid w-full max-w-[520px] gap-8 py-10">
        <div style={order(0)} className="enter text-center">
          <h2 className="text-[clamp(30px,3vw,44px)] font-semibold">{p[role].title}</h2>
          <p className="mx-auto mt-2 max-w-[38ch] text-[15px] text-white/85">{p[role].lead}</p>
        </div>
        <Scene />
      </div>
      <span className="mx-auto inline-flex items-center gap-2.5 rounded-full bg-white/15 py-1.5 pr-4 pl-1.5 text-[13px] text-white backdrop-blur-md">
        <img src={padlockImage} alt="" className="size-7" />
        {p.secure}
      </span>
    </div>
  )
}
