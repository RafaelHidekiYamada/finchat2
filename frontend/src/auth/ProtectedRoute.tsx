import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './AuthContext'

export function ProtectedRoute({ companyOnly = false }: { companyOnly?: boolean }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="grid min-h-screen place-items-center text-sm text-black/50">Carregando sua sessão…</div>
  if (!user) return <Navigate to="/login" replace />
  if (companyOnly && user.document_type !== 'CNPJ') return <Navigate to="/" replace />
  return <Outlet />
}
