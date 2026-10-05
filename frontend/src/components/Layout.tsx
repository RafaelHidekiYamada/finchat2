import { BarChart3, BrainCircuit, Building2, CreditCard, LayoutDashboard, LogOut, ReceiptText, Tags, Users } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const common = [
  ['/', 'Visão geral', LayoutDashboard], ['/transactions', 'Transações', ReceiptText], ['/accounts', 'Contas', CreditCard], ['/categories', 'Categorias', Tags], ['/analysis', 'Análise inteligente', BrainCircuit],
] as const
const company = [['/partners', 'Parceiros', Users], ['/clients', 'Clientes', Users], ['/suppliers', 'Fornecedores', Building2], ['/contracts', 'Contratos', Building2]] as const

export function Layout() {
  const { user, logout } = useAuth()
  const links = user?.document_type === 'CNPJ' ? [...common, ...company] : common
  return <div className="min-h-screen lg:grid lg:grid-cols-[260px_1fr]">
    <aside className="border-b border-black/5 bg-[#103c31] px-4 py-5 text-white lg:min-h-screen lg:border-b-0 lg:px-5">
      <div className="mb-6 flex items-center gap-3 px-2"><div className="grid h-10 w-10 place-items-center rounded-xl bg-mint text-pine"><BarChart3 size={21} /></div><div><div className="font-display text-xl font-extrabold">FinChat</div><div className="text-xs text-white/55">clareza para decidir</div></div></div>
      <nav className="flex gap-1 overflow-x-auto lg:block lg:space-y-1">{links.map(([to, label, Icon]) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `flex min-w-max items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium ${isActive ? 'bg-white text-pine' : 'text-white/70 hover:bg-white/10 hover:text-white'}`}><Icon size={18}/>{label}</NavLink>)}</nav>
      <div className="mt-6 hidden border-t border-white/10 pt-5 lg:block"><div className="px-3 text-sm font-semibold">{user?.name}</div><div className="px-3 text-xs text-white/50">Perfil {user?.document_type}</div><button onClick={logout} className="mt-3 flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm text-white/65 hover:bg-white/10"><LogOut size={17}/>Sair</button></div>
    </aside>
    <main className="min-w-0 px-4 py-7 sm:px-7 lg:px-10 lg:py-9"><Outlet /></main>
  </div>
}
