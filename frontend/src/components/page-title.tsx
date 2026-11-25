import type { ReactNode } from 'react'

/** Titre d'écran : une partie fine, une partie grasse, comme dans la charte. */
export function PageTitle({
  light,
  bold,
  children,
}: {
  light: string
  bold: string
  children?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-6">
      <h1 className="text-[clamp(34px,4.2vw,56px)]">
        {light} <b className="font-semibold">{bold}</b>
      </h1>
      {children}
    </div>
  )
}
