import { Send, X } from 'lucide-react'
import { type FormEvent, useEffect, useRef, useState } from 'react'
import { useMatch } from 'react-router'

import { paths } from '@/app/paths'
import orbImage from '@/assets/copilote-orbe-verre.webp'
import { fr } from '@/i18n/fr'

import { CopilotMessage, type Turn } from './copilot-message'
import { useAsk } from './use-assistant'

const t = fr.assistant

/**
 * Copilote : un panneau latéral qui répond à partir des vraies données. Il connaît la facture
 * ouverte et propose les questions utiles à cet endroit.
 */
export function Copilot() {
  const [open, setOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const ask = useAsk()
  const match = useMatch(paths.invoicePattern)
  const invoiceId = match?.params.invoiceId ?? null
  const end = useRef<HTMLDivElement>(null)
  const suggestions = invoiceId ? t.suggestions.invoice : t.suggestions.general
  const engine = turns.findLast((turn) => turn.role === 'assistant')?.answer.engine

  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end', behavior: 'smooth' })
  }, [turns, ask.isPending])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  function submit(text: string) {
    const trimmed = text.trim()
    if (!trimmed || ask.isPending) return
    setTurns((all) => [...all, { role: 'user', text: trimmed }])
    setQuestion('')
    ask.mutate(
      { question: trimmed, invoiceId },
      { onSuccess: (answer) => setTurns((all) => [...all, { role: 'assistant', answer }]) },
    )
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    submit(question)
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={t.open}
        className={`group fixed right-5 bottom-5 z-40 flex items-center gap-2 rounded-full bg-white py-1.5 pr-4 pl-1.5 shadow-float transition-[transform,opacity] duration-300 ease-out hover:-translate-y-0.5 ${open ? 'pointer-events-none translate-y-3 opacity-0' : ''}`}
      >
        <img
          src={orbImage}
          alt=""
          className="size-10 transition-transform duration-500 ease-out group-hover:rotate-12"
        />
        <span className="text-sm font-semibold text-ink">{t.name}</span>
      </button>

      <aside
        aria-label={t.name}
        aria-hidden={!open}
        className={`fixed top-4 right-4 bottom-4 z-50 flex w-[min(420px,calc(100vw-32px))] flex-col overflow-hidden rounded-[28px] bg-white shadow-[var(--shadow-float)] transition-[transform,opacity] duration-300 ease-out ${open ? 'translate-x-0 opacity-100' : 'pointer-events-none translate-x-[110%] opacity-0'}`}
      >
        <header className="sky flex items-center gap-3 px-5 py-4 text-white">
          <img src={orbImage} alt="" className="float size-11" />
          <div className="min-w-0 flex-1">
            <b className="block text-[17px] font-semibold">{t.name}</b>
            {engine && <span className="label text-[10px] text-white/75">{t.engine(engine)}</span>}
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label={t.close}
            className="grid size-9 place-items-center rounded-full bg-white/15 transition-colors hover:bg-white/25"
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </header>

        <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
          <p className="rounded-[18px] bg-sky-wash px-4 py-3 text-[13.5px] leading-relaxed text-sky-deep">
            {t.intro}
          </p>
          {turns.map((turn, i) => (
            <CopilotMessage key={i} turn={turn} onNavigate={() => setOpen(false)} />
          ))}
          {ask.isPending && <p className="animate-pulse text-sm text-ink-soft">{t.thinking}</p>}
          {ask.isError && (
            <p role="alert" className="text-sm text-coral-ink">
              {t.failed}
            </p>
          )}
          <div ref={end} />
        </div>

        <div className="grid gap-2 border-t border-line px-4 pt-3 pb-4">
          <div className="flex flex-wrap gap-1.5">
            {suggestions.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => submit(s)}
                className="rounded-full bg-ice px-3 py-1.5 text-xs text-ink transition-colors hover:bg-sky-wash"
              >
                {s}
              </button>
            ))}
          </div>
          <form onSubmit={onSubmit} className="flex gap-2">
            <label className="sr-only" htmlFor="copilot-question">
              {t.placeholder}
            </label>
            <input
              id="copilot-question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={t.placeholder}
              maxLength={500}
              className="min-w-0 flex-1 rounded-full bg-ice px-4 py-2.5 text-sm outline-none focus-visible:shadow-[inset_0_0_0_2px_var(--color-sky)]"
            />
            <button
              type="submit"
              aria-label={t.send}
              disabled={!question.trim() || ask.isPending}
              className="grid size-10 place-items-center rounded-full bg-lime text-lime-ink transition-opacity disabled:opacity-40"
            >
              <Send className="size-4" aria-hidden="true" />
            </button>
          </form>
        </div>
      </aside>
    </>
  )
}
