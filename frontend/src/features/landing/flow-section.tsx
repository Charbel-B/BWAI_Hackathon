import { Check, PencilLine } from 'lucide-react'
import type { ReactNode } from 'react'

import uploadImage from '@/assets/depot-pieces-verre.webp'
import messageImage from '@/assets/message-valide-verre.webp'
import { ConfidenceRing } from '@/components/confidence-ring'
import { Reveal } from '@/components/reveal'
import { PaymentBadge, StatusBadge } from '@/components/status-badge'
import { fr } from '@/i18n/fr'

import { SectionTitle } from './section-title'

const t = fr.landing
const s = t.samples
const MARK_SURE =
  'rounded-[5px] bg-sky/15 px-[3px] text-inherit shadow-[inset_0_-2px_0_var(--color-sky)]'
const MARK_UNSURE =
  'rounded-[5px] bg-amber/20 px-[3px] text-inherit shadow-[inset_0_-2px_0_var(--color-amber)]'

function Step({
  index,
  title,
  text,
  children,
  className = '',
}: {
  index: number
  title: string
  text: string
  children: ReactNode
  className?: string
}) {
  return (
    <Reveal index={index - 1} className="grid">
      <article
        className={`lift flex flex-col gap-6 overflow-hidden rounded-card bg-white p-7 shadow-card ${className}`}
      >
        <div className="min-h-[190px] flex-1">{children}</div>
        <div>
          <span className="tabular text-xs text-sky">{`${index} / 4`}</span>
          <h3 className="mt-2 text-[24px] font-semibold tracking-[-0.02em]">{title}</h3>
          <p className="mt-2 max-w-[46ch] text-[15px] leading-relaxed text-ink-soft">{text}</p>
        </div>
      </article>
    </Reveal>
  )
}

/** Le parcours, montré par des fragments de l'interface réelle plutôt que par des icônes. */
export function FlowSection() {
  return (
    <section id="parcours" className="scroll-mt-6 grid gap-8">
      <SectionTitle light={t.flowTitle[0]} bold={t.flowTitle[1]} lead={t.flowLead} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Step index={1} title={t.steps.read.title} text={t.steps.read.text}>
          <div className="relative flex h-full items-center gap-4">
            <pre className="flex-1 rounded-2xl bg-ice p-5 font-mono text-[13px] leading-[1.9] whitespace-pre-wrap text-ink-source">
              {s.source[0]}
              <mark className={MARK_SURE}>{s.source[1]}</mark>
              {s.source[2]}
              <mark className={MARK_UNSURE}>{s.source[3]}</mark>
              {s.source[4]}
              <mark className={MARK_SURE}>{s.source[5]}</mark>
            </pre>
            <img
              src={uploadImage}
              alt=""
              className="hidden w-[150px] shrink-0 drop-shadow-[var(--shadow-object)] sm:block"
            />
          </div>
        </Step>
        <Step index={2} title={t.steps.review.title} text={t.steps.review.text}>
          <ul className="grid gap-2.5">
            <li className="grid grid-cols-[28px_1fr_auto] items-center gap-3 rounded-field bg-amber-wash px-3.5 py-3 outline-[1.5px] -outline-offset-[1.5px] outline-amber outline-dashed">
              <ConfidenceRing value={0.72} tone="amber" />
              <span>
                <span className="label block text-ink-soft">{s.quantityLabel}</span>
                <b className="font-medium">{s.quantityValue}</b>
              </span>
              <span className="rounded-full bg-amber px-2.5 py-1 font-mono text-[11px] text-amber-deep">
                {s.quantityTag}
              </span>
            </li>
            <li className="grid grid-cols-[28px_1fr_auto] items-center gap-3 rounded-field bg-white px-3.5 py-3 shadow-[inset_0_0_0_1px_var(--color-line)]">
              <span className="grid size-7 place-items-center rounded-full bg-lime text-lime-ink">
                <PencilLine className="size-3.5" aria-hidden="true" />
              </span>
              <span>
                <span className="label block text-ink-soft">{s.termsLabel}</span>
                <s className="mr-2 text-ink-soft">{s.termsOld}</s>
                <b className="font-medium">{s.termsNew}</b>
              </span>
              <span className="rounded-full bg-lime px-2.5 py-1 font-mono text-[11px] text-lime-ink">
                {s.corrected}
              </span>
            </li>
            <li className="grid grid-cols-[28px_1fr_auto] items-center gap-3 rounded-field bg-white px-3.5 py-3 shadow-[inset_0_0_0_1px_var(--color-line)]">
              <span className="grid size-7 place-items-center rounded-full bg-ink text-white">
                <Check className="size-3.5" aria-hidden="true" />
              </span>
              <span>
                <span className="label block text-ink-soft">{s.customerLabel}</span>
                <b className="font-medium">{s.customerValue}</b>
              </span>
              <span className="rounded-full bg-ink px-2.5 py-1 font-mono text-[11px] text-white">
                {s.confirmed}
              </span>
            </li>
          </ul>
        </Step>
        <Step
          index={3}
          title={t.steps.validate.title}
          text={t.steps.validate.text}
          className="sky text-white [&_h3]:text-white [&_p]:text-white/85 [&_.text-sky]:text-white/70"
        >
          <div className="grid h-full place-content-center justify-items-center gap-4">
            <StatusBadge status="VALIDATED" />
            <span className="tabular text-[clamp(36px,5vw,60px)] tracking-[-0.03em]">
              {t.sampleNumber}
            </span>
            <span className="label text-white/75">{s.validatedBy}</span>
          </div>
        </Step>
        <Step index={4} title={t.steps.send.title} text={t.steps.send.text}>
          <div className="flex h-full items-center gap-4">
            <img
              src={messageImage}
              alt=""
              className="hidden w-[150px] shrink-0 drop-shadow-[var(--shadow-object)] sm:block"
            />
            <div className="grid flex-1 gap-3">
              <p className="rounded-[18px] rounded-tl-md bg-whatsapp-wash px-4 py-3 text-[13.5px] leading-relaxed text-whatsapp-ink">
                {t.sampleMessage}
                <span className="label mt-2 block text-[10px] opacity-75">
                  WhatsApp · {fr.demo.simulated}
                </span>
              </p>
              <span className="justify-self-start">
                <PaymentBadge status="PAID" />
              </span>
            </div>
          </div>
        </Step>
      </div>
    </section>
  )
}
