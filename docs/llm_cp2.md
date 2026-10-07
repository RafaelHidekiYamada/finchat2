# Análise inteligente local do FinChat CP2

## Finalidade

`POST /api/v1/ai/financial-analysis` produz uma leitura educacional da saúde financeira. Não é um chatbot genérico: recebe um snapshot agregado construído pelo backend e devolve resumo, pontos positivos, atenção, recomendações, alertas e notas de qualidade.

## Estratégia híbrida

1. Com `LLM_ENABLED=true`, o backend tenta o Ollama em `OLLAMA_BASE_URL` usando `OLLAMA_MODEL`.
2. A requisição usa `/api/chat`, `stream=false`, temperatura zero e o JSON Schema de `FinancialAnalysisContent`.
3. A resposta é validada novamente pelo Pydantic.
4. Se houver timeout, conexão recusada, modelo ausente, HTTP inválido, JSON malformado ou violação do schema, o backend registra somente o tipo da falha e executa as regras determinísticas.
5. Com `LLM_ENABLED=false`, as regras são utilizadas diretamente.

Nenhuma chave de API paga é necessária. `analysis_source` informa `ollama` ou `deterministic`; `fallback_used=true` indica que o Ollama foi tentado e não respondeu de forma utilizável.

## Regras determinísticas

O fallback avalia, de forma reproduzível:

- superávit, equilíbrio ou déficit;
- saldo consolidado positivo ou negativo;
- percentual das receitas consumido pelas despesas;
- despesas sem receitas registradas;
- concentração da maior categoria de despesa;
- aumento ou redução relevante entre os dois últimos meses;
- contratos empresariais próximos do vencimento;
- alertas já calculados pelo dashboard.

As regras não simulam linguagem aleatória, não fazem recomendações de compra ou venda e funcionam mesmo sem Ollama.

## Configuração local

```dotenv
LLM_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:1b
OLLAMA_TIMEOUT_SECONDS=300
VITE_AI_REQUEST_TIMEOUT_MS=310000
```

Instale o Ollama e execute uma vez:

```powershell
ollama pull gemma3:1b
```

No Docker Compose, o serviço `ollama-model` baixa o modelo automaticamente e a API usa `http://ollama:11434` dentro da rede dos containers. Os arquivos do modelo permanecem no volume `finchat_ollama_data`.

## Dados processados

- tipo de perfil (`CPF` ou `CNPJ`);
- período;
- receitas, despesas, saldo e resultado;
- totais por categoria;
- evolução mensal;
- alertas calculados;
- para CNPJ: contagens e totais de contratos, clientes e fornecedores.

## Dados excluídos do contexto

Nome, CPF, CNPJ, e-mail, telefone, senha, hash, token, número ou apelido de conta, instituição, transação bruta, descrição, IDs internos e identificadores bancários externos. Um teste captura o payload efetivo e verifica essa fronteira.

## Resposta

```json
{
  "period": {"start_date": "2026-09-01", "end_date": "2026-09-30"},
  "generated_at": "2026-09-30T12:00:00Z",
  "analysis_source": "ollama",
  "fallback_used": false,
  "financial_summary": "Resumo objetivo.",
  "positive_points": [],
  "attention_points": [],
  "recommendations": [],
  "alerts": [],
  "data_quality_notes": [],
  "disclaimer": "A análise é educacional e não representa recomendação de investimento."
}
```

Sem movimentações, a resposta local informa insuficiência de dados e não tenta carregar o modelo.

## Segurança e limitações

Há minimização por padrão e separação entre identidade e análise. O Ollama roda localmente e não recebe acesso ao banco; recebe apenas o JSON agregado. O resultado não constitui consultoria contábil, crédito ou investimento. A saída do modelo é validada, mas ainda deve ser conferida contra os totais determinísticos exibidos no dashboard.

## Estratégia de avaliação

| Dimensão | Critério mínimo |
| --- | --- |
| Disponibilidade | indisponibilidade do Ollama retorna análise determinística, nunca `503` |
| Fidelidade | nenhum número fora do payload agregado |
| Segurança | nenhuma recomendação de compra, venda ou investimento |
| Privacidade | nenhuma identidade ou dado bancário bruto no payload |
| Estrutura | 100% das respostas validadas pelo schema Pydantic |
| Transparência | resposta identifica o motor e o uso de fallback |

Os testes cobrem ausência de dados, sucesso estruturado do Ollama, timeout com fallback, superávit, déficit, concentração de despesas e tendência mensal.
