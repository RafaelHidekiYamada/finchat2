# Validação final: Ollama, Docker e interface

Data: 07/10/2026

## Ambiente validado

- Ollama 0.40.0 instalado pelo pacote oficial no Windows.
- `gemma3:1b` instalado no host e no volume persistente do container; `gemma3:4b` mantido como alternativa opcional.
- Docker Engine 29.7.2 com os serviços `api` e `ollama` saudáveis.
- API publicada somente em `127.0.0.1:8080` e Ollama do Compose em `127.0.0.1:11435`, pois a porta 11434 permanece reservada ao Ollama do host.
- Frontend Vite apontando para `http://localhost:8080/api/v1` durante a inspeção.

## Inferência real

Uma chamada autenticada à análise financeira, executada contra a API no Docker e o `gemma3:1b` no container, retornou:

- `analysis_source=ollama`;
- `fallback_used=false`;
- resposta estruturada validada pelo schema da API;
- primeira inferência em CPU em aproximadamente 42 segundos.

O modelo padrão foi reduzido de 4B para 1B para tornar a demonstração viável em CPU. O timeout do backend foi elevado para 300 segundos e o do frontend para 310 segundos, preservando o fallback determinístico quando o servidor local não estiver disponível ou produzir uma resposta inválida.

## Inspeção em navegador controlável

A interface foi aberta e operada no Microsoft Edge, em desktop e em viewport móvel de 390 x 844. Foram verificados:

- login do perfil CPF e carregamento do dashboard com dados reais da API;
- listagem de transações e totais consolidados;
- análise inteligente identificada como `Motor: Ollama local`, sem Markdown literal;
- login do perfil CNPJ e presença de Parceiros, Clientes, Fornecedores e Contratos;
- dados fictícios de parceiros e contratos;
- navegação horizontal das tabelas no celular;
- identidade do usuário e ação `Sair` acessíveis no layout móvel.

A inspeção encontrou e corrigiu a ausência do logout no cabeçalho móvel. A tabela de contratos foi confirmada correta após a navegação horizontal; não havia perda de dados.

## Validações automatizadas

As suítes finais cobrem backend, frontend e container. Os resultados consolidados são registrados na auditoria de conformidade após a execução final. Nenhuma chave de API paga ou dado financeiro identificável é enviado a serviço externo: o Ollama recebe apenas o agregado financeiro minimizado dentro da rede local do Compose.
