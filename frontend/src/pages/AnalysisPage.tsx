import { useState } from 'react'
import { BrainCircuit, CheckCircle2, Lightbulb, ShieldAlert, Sparkles } from 'lucide-react'
import { Notice, PageHeader } from '../components/Ui'
import { AI_REQUEST_TIMEOUT_MS, api, errorMessage } from '../services/api'
import type { Analysis, ApiSuccess } from '../types'

export function AnalysisPage() {
  const today = new Date().toISOString().slice(0, 10)
  const [range, setRange] = useState({ start_date: `${today.slice(0, 8)}01`, end_date: today })
  const [data, setData] = useState<Analysis | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const generate = async () => {
    setBusy(true)
    setError('')
    try {
      setData((await api.post<ApiSuccess<Analysis>>('/ai/financial-analysis', range, { timeout: AI_REQUEST_TIMEOUT_MS })).data.data)
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  const sections = data ? [
    ['Pontos positivos', data.positive_points, CheckCircle2, 'bg-emerald-50 text-emerald-900'],
    ['Pontos de atenção', data.attention_points, ShieldAlert, 'bg-amber-50 text-amber-900'],
    ['Recomendações', data.recommendations, Lightbulb, 'bg-blue-50 text-blue-900'],
    ['Alertas', data.alerts, ShieldAlert, 'bg-red-50 text-red-900'],
  ] as const : []

  return <>
    <PageHeader eyebrow="Inteligência aplicada" title="Análise inteligente" description="O Ollama processa somente agregados no seu ambiente local. Se ele estiver indisponível, regras financeiras locais mantêm a análise funcionando." />
    <section className="card mb-5 flex flex-wrap items-end gap-3">
      <label><span className="label">Data inicial</span><input type="date" value={range.start_date} onChange={event => setRange({ ...range, start_date: event.target.value })} /></label>
      <label><span className="label">Data final</span><input type="date" value={range.end_date} onChange={event => setRange({ ...range, end_date: event.target.value })} /></label>
      <button className="btn-primary" disabled={busy} onClick={() => void generate()}><Sparkles size={17} />{busy ? 'Analisando…' : 'Gerar análise financeira'}</button>
    </section>
    {error && <Notice>{error}</Notice>}
    {data && <div className="space-y-5">
      <section className="rounded-2xl bg-[#103c31] p-6 text-white shadow-card">
        <div className="flex items-center gap-2 text-sm font-semibold text-[#9dd2b2]"><BrainCircuit size={19} />Resumo do período</div>
        <p className="mt-4 max-w-3xl font-display text-2xl font-bold leading-9">{data.financial_summary}</p>
        <p className="mt-4 text-xs text-white/50">{new Date(`${data.period.start_date}T12:00:00`).toLocaleDateString('pt-BR')} a {new Date(`${data.period.end_date}T12:00:00`).toLocaleDateString('pt-BR')} · gerado em {new Date(data.generated_at).toLocaleString('pt-BR')}</p>
        <p className="mt-2 text-xs font-semibold text-[#9dd2b2]">Motor: {data.analysis_source === 'ollama' ? 'Ollama local' : data.fallback_used ? 'Regras locais (fallback)' : 'Regras locais'}</p>
      </section>
      <div className="grid gap-5 md:grid-cols-2">
        {sections.map(([title, items, Icon, color]) => <section key={title} className="card">
          <h2 className="flex items-center gap-2 font-display text-lg font-bold"><Icon size={19} />{title}</h2>
          {items.length ? <ul className="mt-4 space-y-2">{items.map(item => <li key={item} className={`rounded-xl p-3 text-sm ${color}`}>{item}</li>)}</ul> : <p className="mt-4 text-sm text-black/45">Nenhum item identificado.</p>}
        </section>)}
      </div>
      {data.data_quality_notes.length > 0 && <section className="card"><h2 className="font-semibold">Qualidade dos dados</h2><ul className="mt-2 list-disc pl-5 text-sm text-black/55">{data.data_quality_notes.map(note => <li key={note}>{note}</li>)}</ul></section>}
      <div className="rounded-xl border border-black/10 px-4 py-3 text-xs text-black/50">{data.disclaimer}</div>
    </div>}
  </>
}
