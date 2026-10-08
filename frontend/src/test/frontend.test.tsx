import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'
import { ProtectedRoute } from '../auth/ProtectedRoute'
import { Layout } from '../components/Layout'
import { DashboardPage } from '../pages/DashboardPage'
import { api } from '../services/api'

const auth = vi.hoisted(() => ({ user: null as null | {id:number;name:string;email:string;document_type:'CPF'|'CNPJ'}, loading:false, login:vi.fn(), register:vi.fn(), logout:vi.fn() }))
vi.mock('../auth/AuthContext',()=>({useAuth:()=>auth}))
vi.mock('../services/api',async(importOriginal)=>{const actual=await importOriginal<typeof import('../services/api')>();return{...actual,api:{get:vi.fn()}}})

test('rota protegida redireciona visitante para login',()=>{auth.user=null;render(<MemoryRouter initialEntries={['/privado']}><Routes><Route path="/login" element={<div>Página de login</div>}/><Route element={<ProtectedRoute/>}><Route path="/privado" element={<div>Conteúdo privado</div>}/></Route></Routes></MemoryRouter>);expect(screen.getByText('Página de login')).toBeInTheDocument()})

test('dashboard renderiza os agregados retornados pela API',async()=>{vi.mocked(api.get).mockResolvedValue({data:{data:{start_date:'2026-09-01',end_date:'2026-09-30',consolidated_balance:'100.00',total_income:'150.00',total_expenses:'50.00',net_result:'100.00',monthly_flow:[],expenses_by_category:[],latest_transactions:[],alerts:[],bank_accounts:[],company:null}}} as never);render(<DashboardPage/>);await waitFor(()=>expect(screen.getByText('Saldo consolidado')).toBeInTheDocument());expect(screen.getAllByText(/100,00/).length).toBeGreaterThan(0);expect(screen.getByText('Nenhuma transação encontrada.')).toBeInTheDocument()})

test('layout CNPJ expõe área empresarial e logout também no menu móvel',()=>{auth.user={id:2,name:'Empresa de demonstração',email:'empresa@finchat.demo',document_type:'CNPJ'};auth.logout.mockClear();render(<MemoryRouter><Routes><Route element={<Layout/>}><Route index element={<div>Dashboard</div>}/></Route></Routes></MemoryRouter>);expect(screen.getByRole('link',{name:'Contratos'})).toBeInTheDocument();const logoutButtons=screen.getAllByRole('button',{name:'Sair'});expect(logoutButtons).toHaveLength(2);fireEvent.click(logoutButtons[0]);expect(auth.logout).toHaveBeenCalledOnce()})
