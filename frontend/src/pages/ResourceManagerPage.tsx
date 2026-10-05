import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { BarChart3, Pencil, Plus, Trash2, X } from 'lucide-react'
import { Empty, Notice, PageHeader, money } from '../components/Ui'
import { api, errorMessage } from '../services/api'
import type { ApiSuccess } from '../types'

type ResourceKind = 'accounts' | 'categories' | 'partners' | 'contracts'
type PartnerFilter = 'CLIENT' | 'SUPPLIER'
interface RecordItem { id: number; [key: string]: unknown }
interface Field { key: string; label: string; type?: string; options?: Array<[string, string]>; source?: 'partners' }
interface FinancialSummary { total_income: string; total_expenses: string; received: string; paid: string; balance: string; expected_amount: string; outstanding_amount: string }
interface Config { endpoint: string; eyebrow: string; title: string; description: string; fields: Field[]; blank: Record<string, string>; columns: Array<[string, string]> }

const configs: Record<ResourceKind, Config> = {
  accounts: { endpoint: '/bank-accounts', eyebrow: 'Gestão financeira', title: 'Contas bancárias', description: 'Cadastre contas locais; nenhuma credencial bancária é armazenada.', blank: { institution: '', nickname: '', account_type: 'CHECKING', initial_balance: '0.00' }, fields: [{ key: 'institution', label: 'Instituição' }, { key: 'nickname', label: 'Apelido' }, { key: 'account_type', label: 'Tipo', options: [['CHECKING', 'Conta corrente'], ['SAVINGS', 'Poupança'], ['PAYMENT', 'Pagamento']] }, { key: 'initial_balance', label: 'Saldo inicial' }], columns: [['nickname', 'Conta'], ['institution', 'Instituição'], ['account_type', 'Tipo']] },
  categories: { endpoint: '/categories', eyebrow: 'Organização', title: 'Categorias', description: 'Organize receitas e despesas com categorias próprias.', blank: { name: '', type: 'EXPENSE' }, fields: [{ key: 'name', label: 'Nome' }, { key: 'type', label: 'Tipo', options: [['EXPENSE', 'Despesa'], ['INCOME', 'Receita']] }], columns: [['name', 'Categoria'], ['type', 'Tipo']] },
  partners: { endpoint: '/partners', eyebrow: 'Área empresarial', title: 'Parceiros', description: 'Gerencie clientes e fornecedores vinculados ao CNPJ.', blank: { name: '', type: 'CLIENT', document: '', email: '' }, fields: [{ key: 'name', label: 'Nome' }, { key: 'type', label: 'Tipo', options: [['CLIENT', 'Cliente'], ['SUPPLIER', 'Fornecedor']] }, { key: 'document', label: 'Documento' }, { key: 'email', label: 'E-mail', type: 'email' }], columns: [['name', 'Parceiro'], ['type', 'Tipo'], ['email', 'E-mail']] },
  contracts: { endpoint: '/contracts', eyebrow: 'Área empresarial', title: 'Contratos', description: 'Acompanhe valores esperados, vigência e situação dos contratos.', blank: { title: '', partner_id: '', type: 'INCOME', expected_amount: '0.00', start_date: new Date().toISOString().slice(0, 10), end_date: '', status: 'ACTIVE' }, fields: [{ key: 'title', label: 'Título' }, { key: 'partner_id', label: 'Parceiro', source: 'partners' }, { key: 'type', label: 'Tipo', options: [['INCOME', 'Receita'], ['EXPENSE', 'Despesa']] }, { key: 'expected_amount', label: 'Valor esperado' }, { key: 'start_date', label: 'Início', type: 'date' }, { key: 'end_date', label: 'Fim', type: 'date' }, { key: 'status', label: 'Status', options: [['ACTIVE', 'Ativo'], ['COMPLETED', 'Concluído'], ['CANCELLED', 'Cancelado']] }], columns: [['title', 'Contrato'], ['status', 'Status'], ['expected_amount', 'Valor esperado']] },
}

export function ResourceManagerPage({ kind, partnerFilter }: { kind: ResourceKind; partnerFilter?: PartnerFilter }) {
  const baseConfig = configs[kind]
  const config = useMemo(() => {
    if (kind !== 'partners' || !partnerFilter) return baseConfig
    const client = partnerFilter === 'CLIENT'
    return { ...baseConfig, title: client ? 'Clientes' : 'Fornecedores', description: client ? 'Gerencie clientes e acompanhe os valores recebidos.' : 'Gerencie fornecedores e acompanhe os valores pagos.', blank: { ...baseConfig.blank, type: partnerFilter }, fields: baseConfig.fields.filter(field => field.key !== 'type') }
  }, [baseConfig, kind, partnerFilter])
  const [items, setItems] = useState<RecordItem[]>([])
  const [partners, setPartners] = useState<RecordItem[]>([])
  const [form, setForm] = useState(config.blank)
  const [editing, setEditing] = useState<number | null>(null)
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')
  const [summary, setSummary] = useState<{ label: string; data: FinancialSummary } | null>(null)

  const load = async () => {
    try {
      const records = (await api.get<ApiSuccess<RecordItem[]>>(config.endpoint)).data.data
      setItems(partnerFilter ? records.filter(item => item.type === partnerFilter) : records)
      if (kind === 'contracts') setPartners((await api.get<ApiSuccess<RecordItem[]>>('/partners')).data.data)
    } catch (requestError) { setError(errorMessage(requestError)) }
  }
  useEffect(() => { setForm(config.blank); setEditing(null); setOpen(false); setSummary(null); void load() }, [config.endpoint, partnerFilter])

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError('')
    const payload = Object.fromEntries(Object.entries(form).map(([key, value]) => [key, key.endsWith('_id') ? Number(value) : value === '' && ['document', 'email', 'end_date'].includes(key) ? null : value]))
    try {
      if (editing) await api.put(`${config.endpoint}/${editing}`, payload); else await api.post(config.endpoint, payload)
      setForm(config.blank); setOpen(false); setEditing(null); await load()
    } catch (requestError) { setError(errorMessage(requestError)) }
  }
  const edit = (item: RecordItem) => { const values = { ...config.blank }; for (const key of Object.keys(values)) values[key] = item[key] == null ? '' : String(item[key]); setForm(values); setEditing(item.id); setOpen(true) }
  const remove = async (id: number) => { if (!confirm('Excluir este registro?')) return; try { await api.delete(`${config.endpoint}/${id}`); await load() } catch (requestError) { setError(errorMessage(requestError)) } }
  const showSummary = async (item: RecordItem) => { try { const data = (await api.get<ApiSuccess<FinancialSummary>>(`${config.endpoint}/${item.id}/financial-summary`)).data.data; setSummary({ label: String(item.name || item.title), data }) } catch (requestError) { setError(errorMessage(requestError)) } }
  const hasSummary = kind === 'partners' || kind === 'contracts'

  return <>
    <PageHeader eyebrow={config.eyebrow} title={config.title} description={config.description} action={<button className="btn-primary" onClick={() => { setForm(config.blank); setEditing(null); setOpen(true) }}><Plus size={17} />Adicionar</button>} />
    {error && <div className="mb-4"><Notice>{error}</Notice></div>}
    {summary && <section className="card mb-5"><div className="flex items-center justify-between"><h2 className="font-display text-xl font-bold">Resumo · {summary.label}</h2><button onClick={() => setSummary(null)}><X size={18} /></button></div><div className="mt-5 grid gap-4 sm:grid-cols-3">{[['Recebido', summary.data.received], ['Pago', summary.data.paid], ['Saldo', summary.data.balance], ['Previsto', summary.data.expected_amount], ['Em aberto', summary.data.outstanding_amount]].map(([label, value]) => <div key={label}><div className="label">{label}</div><div className="font-display text-xl font-bold">{money(value)}</div></div>)}</div></section>}
    {open && <form onSubmit={submit} className="card mb-5"><div className="mb-5 flex items-center justify-between"><h2 className="font-display text-xl font-bold">{editing ? 'Editar' : 'Novo registro'}</h2><button type="button" onClick={() => setOpen(false)}><X size={19} /></button></div><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{config.fields.map(field => <label key={field.key}><span className="label">{field.label}</span>{field.source === 'partners' ? <select value={form[field.key]} onChange={event => setForm({ ...form, [field.key]: event.target.value })} required><option value="">Selecione</option>{partners.map(partner => <option key={partner.id} value={partner.id}>{String(partner.name)}</option>)}</select> : field.options ? <select value={form[field.key]} onChange={event => setForm({ ...form, [field.key]: event.target.value })}>{field.options.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select> : <input type={field.type || 'text'} value={form[field.key]} onChange={event => setForm({ ...form, [field.key]: event.target.value })} required={!['document', 'email', 'end_date'].includes(field.key)} />}</label>)}</div><button className="btn-primary mt-5">Salvar</button></form>}
    <section className="card overflow-x-auto">{items.length ? <table className="w-full min-w-[560px] text-left text-sm"><thead className="text-xs uppercase text-black/40"><tr>{config.columns.map(([, label]) => <th key={label} className="pb-3">{label}</th>)}<th className="text-right">Ações</th></tr></thead><tbody>{items.map(item => <tr key={item.id} className="border-t border-black/5">{config.columns.map(([key]) => <td key={key} className="py-3">{String(item[key] ?? '—')}</td>)}<td><div className="flex justify-end gap-1">{hasSummary && <button aria-label="Resumo financeiro" className="rounded-lg p-2 text-pine hover:bg-mint" onClick={() => void showSummary(item)}><BarChart3 size={16} /></button>}<button aria-label="Editar" className="rounded-lg p-2 hover:bg-black/5" onClick={() => edit(item)}><Pencil size={16} /></button><button aria-label="Excluir" className="rounded-lg p-2 text-coral hover:bg-red-50" onClick={() => void remove(item.id)}><Trash2 size={16} /></button></div></td></tr>)}</tbody></table> : <Empty>Nenhum registro cadastrado.</Empty>}</section>
  </>
}
