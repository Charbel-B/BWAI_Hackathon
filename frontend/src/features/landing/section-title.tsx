/** Titre de section de la landing : une partie fine, une partie grasse, une phrase d'appui. */
export function SectionTitle({
  light,
  bold,
  lead,
  tone = 'dark',
}: {
  light: string
  bold: string
  lead?: string
  tone?: 'dark' | 'light' | 'lime'
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1fr] lg:items-end">
      <h2 className="text-[clamp(34px,4.6vw,64px)]">
        {light} <b className="font-semibold">{bold}</b>
      </h2>
      {lead && (
        <p
          className={`max-w-[52ch] text-[16px] leading-relaxed ${{ dark: 'text-ink-soft', light: 'text-white/75', lime: 'text-lime-ink/80' }[tone]}`}
        >
          {lead}
        </p>
      )}
    </div>
  )
}
