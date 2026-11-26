import { ArrowUpRight, LoaderCircle } from 'lucide-react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'ink' | 'ghost' | 'quiet'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-lime text-lime-ink shadow-lime hover:bg-lime-hover',
  ink: 'bg-ink text-white hover:bg-ink-hover',
  ghost:
    'bg-white text-ink shadow-[inset_0_0_0_1px_var(--color-line)] hover:shadow-[inset_0_0_0_1px_var(--color-ink-soft)]',
  quiet: 'bg-transparent text-ink-soft hover:text-ink hover:bg-white/60',
}

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  pending?: boolean
  arrow?: boolean
  icon?: ReactNode
}

/** Bouton en pilule. Le citron est réservé à l'action principale d'un écran. */
export function Button({
  variant = 'ghost',
  pending = false,
  arrow = false,
  icon,
  children,
  className = '',
  disabled,
  ...rest
}: Props) {
  return (
    <button
      {...rest}
      disabled={disabled === true || pending}
      aria-busy={pending}
      className={`inline-flex items-center justify-center gap-2.5 rounded-full px-5 py-3 text-sm font-medium transition-[background,box-shadow,transform,opacity] duration-200 ease-out active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-45 disabled:active:scale-100 ${VARIANTS[variant]} ${className}`}
    >
      {pending ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : icon}
      {children}
      {arrow && (
        <span className="-mr-2.5 grid size-[26px] place-items-center rounded-full bg-night text-white">
          <ArrowUpRight className="size-3.5" strokeWidth={2.4} aria-hidden="true" />
        </span>
      )}
    </button>
  )
}
