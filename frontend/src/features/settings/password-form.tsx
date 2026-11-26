import { Check, CircleCheck } from 'lucide-react'
import { type FormEvent, useState } from 'react'

import { Button } from '@/components/button'
import { fr } from '@/i18n/fr'

const t = fr.settings
const field =
  'w-full rounded-2xl bg-ice px-4 py-3 text-[15px] outline-none shadow-[inset_0_0_0_1px_var(--color-line)] focus-visible:shadow-[inset_0_0_0_2px_var(--color-sky)]'

/**
 * Changement de mot de passe, simulé : le backend de démonstration n'a que des comptes fixes.
 * Les règles sont vérifiées pour montrer le parcours, et le résultat le dit franchement.
 */
export function PasswordForm() {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [done, setDone] = useState(false)
  const checks = [
    next.length >= 12,
    /[a-z]/i.test(next) && /\d/.test(next),
    next !== '' && next === confirm,
  ]
  const valid = current !== '' && checks.every(Boolean)

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!valid) return
    setDone(true)
    setCurrent('')
    setNext('')
    setConfirm('')
  }

  return (
    <form onSubmit={submit} className="grid gap-3">
      {[
        {
          id: 'current',
          label: t.current,
          value: current,
          set: setCurrent,
          auto: 'current-password',
        },
        { id: 'next', label: t.next, value: next, set: setNext, auto: 'new-password' },
        { id: 'confirm', label: t.confirm, value: confirm, set: setConfirm, auto: 'new-password' },
      ].map((f) => (
        <label key={f.id} className="grid gap-1.5">
          <span className="label text-ink-soft">{f.label}</span>
          <input
            type="password"
            autoComplete={f.auto}
            value={f.value}
            onChange={(e) => {
              setDone(false)
              f.set(e.target.value)
            }}
            className={field}
          />
        </label>
      ))}
      <ul className="grid gap-1.5 py-1">
        {t.rules.map((rule, index) => (
          <li
            key={rule}
            className={`flex items-center gap-2 text-sm transition-colors duration-200 ${checks[index] ? 'text-sky-deep' : 'text-ink-soft'}`}
          >
            <span
              className={`grid size-5 place-items-center rounded-full transition-colors duration-200 ${checks[index] ? 'bg-sky text-white' : 'bg-mist'}`}
            >
              <Check className="size-3" strokeWidth={3} aria-hidden="true" />
            </span>
            {rule}
          </li>
        ))}
      </ul>
      <Button type="submit" variant="ink" disabled={!valid} className="justify-self-start">
        {t.passwordSubmit}
      </Button>
      {done && (
        <p
          role="status"
          className="flex items-start gap-2 rounded-xl bg-sky-wash px-3.5 py-2.5 text-sm text-sky-deep"
        >
          <CircleCheck className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          {t.passwordDone}
        </p>
      )}
    </form>
  )
}
