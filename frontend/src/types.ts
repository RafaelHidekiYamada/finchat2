export type UserType = 'CPF' | 'CNPJ'
export interface User { id: number; name: string; email: string; document_type: UserType }
export interface ApiSuccess<T> { message: string; data: T }
export interface ApiError { error: { code: string; message: string; details: Array<{ field?: string; message?: string }> } }
export interface Transaction { id: number; description: string; amount: string; date: string; type: 'INCOME' | 'EXPENSE'; category_id: number; bank_account_id: number | null; partner_id: number | null; contract_id: number | null; origin: string }
export interface Dashboard {
  start_date: string; end_date: string; consolidated_balance: string; total_income: string; total_expenses: string; net_result: string
  monthly_flow: Array<{ month: string; income: string; expenses: string }>
  expenses_by_category: Array<{ category_id: number; category_name: string; total: string }>
  latest_transactions: Transaction[]; alerts: string[]
  bank_accounts: Array<{ id: number; institution: string; nickname: string; balance: string }>
  company: null | { active_contracts: number; received: string; paid: string; clients: unknown[]; suppliers: unknown[]; contracts_due_soon: unknown[]; top_partners: unknown[] }
}
export interface Analysis { period: { start_date: string; end_date: string }; generated_at: string; analysis_source: 'ollama' | 'deterministic'; fallback_used: boolean; financial_summary: string; positive_points: string[]; attention_points: string[]; recommendations: string[]; alerts: string[]; data_quality_notes: string[]; disclaimer: string }
