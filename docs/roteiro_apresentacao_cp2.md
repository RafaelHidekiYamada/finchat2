# Roteiro de apresentação — FinChat CP2 (6 a 8 minutos)

## 0:00–0:40 — Contexto e evolução

Apresentar o problema: CPF e CNPJ precisam transformar movimentações em visão prática. Mostrar que o CP1 já possuía API, JWT, CRUDs, regras, banco e simuladores. O CP2 mantém tudo e acrescenta interface, dashboard consolidado, otimizações, revisão do banco e IA responsável.

## 0:40–1:30 — Arquitetura

Abrir `docs/arquitetura_cp2.md`. Explicar React → FastAPI → services/repositories → SQL e a camada híbrida Ollama local + regras determinísticas. Reforçar que Open Finance e WhatsApp continuam simulados.

## 1:30–2:40 — Frontend e comunicação

1. Fazer login com usuário de demonstração.
2. Mostrar proteção de rotas e menu diferente entre CPF/CNPJ.
3. Abrir transações, cadastrar uma despesa e editá-la.
4. Mostrar no DevTools que o frontend chama a API central e envia JWT.

## 2:40–3:40 — Dashboard real

Voltar à visão geral. Alterar período. Destacar cards, fluxo mensal, despesas por categoria, transações e alertas. Explicar que uma chamada a `/dashboard/overview` reúne tudo e que não existem arrays financeiros fixos no React.

## 3:40–4:30 — Banco e otimizações

Mostrar a migration `0002`, os índices compostos e constraints de parceiros. Demonstrar a paginação de transações no Swagger com `page_size=1`, filtros e ordenação. Citar limite máximo de 100 e isolamento por usuário.

## 4:30–5:15 — Área CNPJ

Entrar com CNPJ. Abrir parceiros e contratos. Mostrar contrato próximo do vencimento e resumo no dashboard. Explicar bloqueio 403 para CPF.

## 5:15–6:20 — Análise inteligente

Abrir “Análise inteligente”, selecionar período e gerar. Mostrar o formato estruturado, o motor utilizado e o aviso educacional. Explicar a minimização: somente agregados, nunca documento, contato, token ou conta. Parar o Ollama e demonstrar que as regras determinísticas mantêm a rota funcionando com `fallback_used=true`.

## 6:20–7:10 — Qualidade

Executar rapidamente ou mostrar evidências de `pytest`, `npm test`, `npm run build`, migrations, `/health` e `/docs`. Citar testes de sanitização do payload e isolamento.

## 7:10–7:40 — CP3

Encerrar com próximos passos: Open Finance homologado, WhatsApp oficial, observabilidade/rate limiting, consentimento/privacidade de produção e avaliações contínuas da IA. Não prometer integrações que ainda não existem.
