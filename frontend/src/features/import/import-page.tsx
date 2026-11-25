import { CircleAlert, FileText } from 'lucide-react'
import { type DragEvent, useRef, useState } from 'react'
import { useNavigate } from 'react-router'

import uploadImage from '@/assets/depot-pieces-verre.webp'
import { Button } from '@/components/button'
import { PageTitle } from '@/components/page-title'
import { paths } from '@/app/paths'
import { fr } from '@/i18n/fr'
import { problemMessage } from '@/lib/problem-message'

import { useImportDocument } from './use-import'

const t = fr.import

/** Import d'une pièce : fichier déposé ou message collé, puis direction la revue. */
export function ImportPage() {
  const navigate = useNavigate()
  const upload = useImportDocument()
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [text, setText] = useState('')

  function send(file: File) {
    upload.mutate(file, { onSuccess: (result) => void navigate(paths.invoice(result.invoice.id)) })
  }

  function drop(event: DragEvent) {
    event.preventDefault()
    setDragging(false)
    const file = event.dataTransfer.files[0]
    if (file) send(file)
  }

  return (
    <div className="grid gap-5 rounded-card bg-white p-6 shadow-card sm:p-8">
      <PageTitle light={t.titleLight} bold={t.titleBold} />
      <p className="max-w-[62ch] text-[15px] leading-relaxed text-ink-soft">{t.lead}</p>

      <div className="grid gap-5 lg:grid-cols-2">
        <button
          type="button"
          onClick={() => input.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={drop}
          disabled={upload.isPending}
          className={`group relative grid min-h-[280px] place-items-center overflow-hidden rounded-[22px] p-8 text-center transition-[box-shadow,background] duration-300 ease-out ${dragging ? 'bg-sky-wash shadow-[inset_0_0_0_2px_var(--color-sky)]' : 'bg-ice shadow-[inset_0_0_0_1.5px_var(--color-sky-soft)] hover:shadow-[inset_0_0_0_2px_var(--color-sky)]'}`}
        >
          <span className="grid justify-items-center gap-4">
            <img
              src={uploadImage}
              alt=""
              className="w-[150px] drop-shadow-[var(--shadow-object)] transition-transform duration-300 ease-out group-hover:-translate-y-1.5"
            />
            <span className="text-lg font-medium">{upload.isPending ? t.reading : t.drop}</span>
            <span className="text-sm text-ink-soft">{t.dropHint}</span>
          </span>
          <input
            ref={input}
            type="file"
            accept=".txt,text/plain"
            className="sr-only"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) send(file)
              e.target.value = ''
            }}
          />
        </button>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (text.trim()) send(new File([text], t.pastedName, { type: 'text/plain' }))
          }}
          className="grid gap-3"
        >
          <label htmlFor="pasted" className="flex items-center gap-2 text-sm font-medium">
            <FileText className="size-4 text-sky" aria-hidden="true" />
            {t.paste}
          </label>
          <textarea
            id="pasted"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={t.pastePlaceholder}
            rows={9}
            className="min-h-[200px] resize-y rounded-[22px] bg-ice p-5 font-mono text-[13px] leading-relaxed outline-none placeholder:text-ink-soft/60 focus-visible:shadow-[inset_0_0_0_2px_var(--color-sky)]"
          />
          <Button
            type="submit"
            variant="primary"
            arrow
            disabled={!text.trim()}
            pending={upload.isPending}
            className="justify-self-start"
          >
            {t.pasteSubmit}
          </Button>
        </form>
      </div>

      {upload.isPending && (
        <ol aria-live="polite" className="flex flex-wrap gap-2">
          {t.steps.map((step, index) => (
            <li
              key={step}
              className="label animate-pulse rounded-full bg-sky-wash px-3 py-2 text-sky-deep"
              style={{ animationDelay: `${index * 180}ms` }}
            >
              {step}
            </li>
          ))}
        </ol>
      )}
      {upload.isError && (
        <p
          role="alert"
          className="flex items-center gap-2.5 rounded-field bg-coral-wash px-4 py-3 text-sm text-coral-ink"
        >
          <CircleAlert className="size-4" aria-hidden="true" />
          {`${t.failed} ${problemMessage(upload.error)}`}
        </p>
      )}
    </div>
  )
}
