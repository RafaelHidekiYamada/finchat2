import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { errorMessage } from '../services/api'
import { Notice } from '../components/Ui'

export function LoginPage() {
  const { user, login } = useAuth(); const navigate = useNavigate(); const [email, setEmail] = useState(''); const [password, setPassword] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  if (user) return <Navigate to="/" replace />
  const submit = async (event: FormEvent) => { event.preventDefault(); setBusy(true); setError(''); try { await login(email, password); navigate('/') } catch (err) { setError(errorMessage(err)) } finally { setBusy(false) } }
  return <div className="grid min-h-screen bg-[#103c31] lg:grid-cols-2"><section className="hidden place-content-center p-14 text-white lg:grid"><div className="max-w-lg"><span className="rounded-full bg-white/10 px-4 py-2 text-xs font-bold uppercase tracking-widest">FinChat CP2</span><h1 className="mt-7 font-display text-6xl font-extrabold leading-[1.05]">Dinheiro claro.<br/><span className="text-[#9dd2b2]">Decisões leves.</span></h1><p className="mt-6 max-w-md text-lg leading-8 text-white/65">Dashboard real, organização financeira e análise inteligente em um só lugar.</p></div></section><section className="grid place-items-center bg-cream p-5"><form onSubmit={submit} className="card w-full max-w-md p-7 sm:p-9"><div className="text-sm font-bold text-pine">Bem-vindo de volta</div><h2 className="mt-2 font-display text-3xl font-extrabold">Entre na sua conta</h2><p className="mb-7 mt-2 text-sm text-black/50">Use seu e-mail e senha cadastrados.</p>{error && <div className="mb-4"><Notice>{error}</Notice></div>}<label className="label">E-mail</label><input type="email" value={email} onChange={e=>setEmail(e.target.value)} required/><label className="label mt-4">Senha</label><input type="password" value={password} onChange={e=>setPassword(e.target.value)} required/><button className="btn-primary mt-6 w-full" disabled={busy}>{busy ? 'Entrando…' : 'Entrar'}</button><p className="mt-6 text-center text-sm text-black/55">Ainda não tem conta? <Link className="font-semibold text-pine" to="/register">Cadastre-se</Link></p></form></section></div>
}
