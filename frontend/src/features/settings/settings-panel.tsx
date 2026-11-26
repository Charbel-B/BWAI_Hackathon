import type { ReactNode } from 'react'

import { Reveal } from '@/components/reveal'

/** Bloc de la page Paramètres : un titre, un texte d'appui, le contenu. */
export function SettingsPanel({
  title,
  index,
  children,
  aside,
}: {
  title: string
  index: number
  children: ReactNode
  aside?: ReactNode
}) {
  return (
    <Reveal index={index} className="grid">
      <section className="grid content-start gap-5 rounded-card bg-white p-6 shadow-card sm:p-7">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-[22px] font-semibold tracking-[-0.02em]">{title}</h2>
          {aside}
        </div>
        {children}
      </section>
    </Reveal>
  )
}
