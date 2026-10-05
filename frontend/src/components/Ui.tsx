import type { ReactNode } from 'react'

export const money = (value: string | number) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value))
export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) { return <header className="mb-7 flex flex-wrap items-end justify-between gap-4"><div><div className="mb-2 text-xs font-bold uppercase tracking-[.2em] text-pine/70">{eyebrow}</div><h1 className="font-display text-3xl font-extrabold tracking-tight sm:text-4xl">{title}</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-black/55">{description}</p></div>{action}</header> }
export function Empty({ children }: { children: ReactNode }) { return <div className="rounded-2xl border border-dashed border-black/15 p-8 text-center text-sm text-black/50">{children}</div> }
export function Notice({ kind = 'error', children }: { kind?: 'error' | 'success'; children: ReactNode }) { return <div className={`rounded-xl px-4 py-3 text-sm ${kind === 'error' ? 'bg-red-50 text-red-800' : 'bg-mint text-pine'}`}>{children}</div> }
