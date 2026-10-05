# Otimizações da API no CP2

## Transações limitadas e previsíveis

`GET /api/v1/transactions` ganhou `page`, `page_size`, filtros e ordenação. `page_size` aceita no máximo 100. Para preservar clientes do CP1, `limit/offset` continuam disponíveis, também limitados a 100; sem os novos parâmetros a resposta mantém o envelope legado.

Campos de ordenação permitidos: `occurred_at` (alias de `date`), `date`, `amount`, `created_at` e `description`. A lista permitida impede ordenação por SQL arbitrário.

O contrato CP2 é:

```json
{
  "data": [],
  "meta": { "page": 1, "page_size": 20, "total": 0, "total_pages": 0 }
}
```

## Endpoint consolidado

`GET /api/v1/dashboard/overview` substitui múltiplas chamadas do frontend. Ele devolve em uma requisição:

- saldo consolidado até a data final;
- receitas, despesas e resultado do período;
- evolução mensal;
- despesas agrupadas por categoria;
- cinco transações recentes;
- saldos por conta e alertas;
- visão empresarial adicional para CNPJ.

As somas e agrupamentos usam `SUM`, `CASE`, `GROUP BY` e filtros no banco. Apenas as séries pequenas necessárias ao gráfico e os cinco registros recentes chegam à aplicação.

## Consultas e N+1

- O dashboard seleciona somente colunas necessárias nas agregações.
- Categorias, contas e parceiros são agrupados por joins, sem consulta por item.
- A listagem de transações não serializa relacionamentos e portanto não dispara lazy loads.
- Resumos empresariais usam agregações por parceiro e contrato.

## Isolamento e validação

Filtros com IDs passam por `owned`, que combina chave do recurso e `user_id`. Períodos invertidos retornam 400; `page_size > 100` retorna 422. O dashboard limita o intervalo a três anos para impedir respostas desproporcionais.

## Índices usados

- `transactions(user_id, date)` para período e ordenação;
- `transactions(user_id, bank_account_id, category_id)` para filtros financeiros;
- `contracts(user_id, status)` e `contracts(user_id, end_date)`;
- `partners(user_id, type)`.

## Frontend

Rotas são carregadas pelo React Router; o cliente Axios centraliza base URL, token e expiração. Gráficos consomem diretamente o endpoint consolidado. O build de produção é minificado pelo Vite.
