import { useEffect, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { Notice, PageHeader, money } from '../components/Ui'
import { api, errorMessage } from '../services/api'
import type { ApiSuccess, Transaction } from '../types'

export function TransactionDetailPage(){const{id}=useParams();const[item,setItem]=useState<Transaction|null>(null);const[error,setError]=useState('');useEffect(()=>{api.get<ApiSuccess<Transaction>>(`/transactions/${id}`).then(r=>setItem(r.data.data)).catch(e=>setError(errorMessage(e)))},[id]);return <><PageHeader eyebrow="Transações" title="Detalhes da movimentação" description="Informações persistidas e validadas pela API." action={<Link className="btn-secondary" to="/transactions"><ArrowLeft size={16}/>Voltar</Link>}/>{error&&<Notice>{error}</Notice>}{item&&<div className="card grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{[['Descrição',item.description],['Valor',money(item.amount)],['Data',new Date(`${item.date}T12:00:00`).toLocaleDateString('pt-BR')],['Tipo',item.type==='INCOME'?'Receita':'Despesa'],['Origem',item.origin],['Conta',item.bank_account_id?`#${item.bank_account_id}`:'Dinheiro / sem conta']].map(([label,value])=><div key={label}><div className="label">{label}</div><div className="font-semibold">{value}</div></div>)}</div>}</>}
