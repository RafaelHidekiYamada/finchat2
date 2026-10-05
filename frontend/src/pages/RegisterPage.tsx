import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { errorMessage } from '../services/api'
import { Notice } from '../components/Ui'

export function RegisterPage() {
  const { register } = useAuth(); const navigate = useNavigate(); const [error, setError] = useState(''); const [busy, setBusy] = useState(false); const [form, setForm] = useState({ name:'', email:'', whatsapp:'', document:'', document_type:'CPF', password:'' })
  const submit = async (e: FormEvent) => { e.preventDefault(); setBusy(true); setError(''); try { await register(form); navigate('/') } catch(err) { setError(errorMessage(err)) } finally { setBusy(false) } }
  return <div className="grid min-h-screen place-items-center bg-[#103c31] p-5"><form onSubmit={submit} className="card w-full max-w-2xl p-7"><h1 className="font-display text-3xl font-extrabold">Crie sua conta</h1><p className="mb-6 mt-2 text-sm text-black/50">Escolha CPF para finanças pessoais ou CNPJ para recursos empresariais.</p>{error && <div className="mb-4"><Notice>{error}</Notice></div>}<div className="grid gap-4 sm:grid-cols-2">{[['name','Nome'],['email','E-mail'],['whatsapp','WhatsApp'],['document','CPF ou CNPJ'],['password','Senha']].map(([key,label])=><label key={key}><span className="label">{label}</span><input type={key==='password'?'password':key==='email'?'email':'text'} value={form[key as keyof typeof form]} onChange={e=>setForm({...form,[key]:e.target.value})} required/></label>)}<label><span className="label">Tipo de perfil</span><select value={form.document_type} onChange={e=>setForm({...form,document_type:e.target.value})}><option>CPF</option><option>CNPJ</option></select></label></div><button className="btn-primary mt-6 w-full" disabled={busy}>{busy?'Criando…':'Criar conta'}</button><p className="mt-5 text-center text-sm">Já tem conta? <Link to="/login" className="font-semibold text-pine">Entrar</Link></p></form></div>
}
