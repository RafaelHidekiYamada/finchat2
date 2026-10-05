import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { Layout } from './components/Layout'

const AnalysisPage = lazy(() => import('./pages/AnalysisPage').then(module => ({ default: module.AnalysisPage })))
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(module => ({ default: module.DashboardPage })))
const LoginPage = lazy(() => import('./pages/LoginPage').then(module => ({ default: module.LoginPage })))
const RegisterPage = lazy(() => import('./pages/RegisterPage').then(module => ({ default: module.RegisterPage })))
const ResourceManagerPage = lazy(() => import('./pages/ResourceManagerPage').then(module => ({ default: module.ResourceManagerPage })))
const TransactionDetailPage = lazy(() => import('./pages/TransactionDetailPage').then(module => ({ default: module.TransactionDetailPage })))
const TransactionsPage = lazy(() => import('./pages/TransactionsPage').then(module => ({ default: module.TransactionsPage })))

export default function App(){return <BrowserRouter><AuthProvider><Suspense fallback={<div className="grid min-h-screen place-items-center text-sm text-black/50">Carregando…</div>}><Routes><Route path="/login" element={<LoginPage/>}/><Route path="/register" element={<RegisterPage/>}/><Route element={<ProtectedRoute/>}><Route element={<Layout/>}><Route index element={<DashboardPage/>}/><Route path="transactions" element={<TransactionsPage/>}/><Route path="transactions/:id" element={<TransactionDetailPage/>}/><Route path="accounts" element={<ResourceManagerPage kind="accounts"/>}/><Route path="categories" element={<ResourceManagerPage kind="categories"/>}/><Route path="analysis" element={<AnalysisPage/>}/><Route element={<ProtectedRoute companyOnly/>}><Route path="partners" element={<ResourceManagerPage kind="partners"/>}/><Route path="clients" element={<ResourceManagerPage kind="partners" partnerFilter="CLIENT"/>}/><Route path="suppliers" element={<ResourceManagerPage kind="partners" partnerFilter="SUPPLIER"/>}/><Route path="contracts" element={<ResourceManagerPage kind="contracts"/>}/></Route></Route></Route><Route path="*" element={<LoginPage/>}/></Routes></Suspense></AuthProvider></BrowserRouter>}
