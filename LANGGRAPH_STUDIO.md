# Rodando o grafo no LangGraph Studio (local)

Este guia mostra como ligar o grafo do `etapa07_grafo.py` ao servidor de desenvolvimento do LangGraph (`langgraph dev`) e
ao Studio, e como testar a integração. O grafo, as chamadas ao LLM e o MCP continuam rodando **na sua máquina**; o Studio
web é só a interface.

## 1. O que é cada peça

| Peça | Para que serve |
|---|---|
| `etapa07_grafo.py` | O grafo. A função `construir(checkpointer=None)` devolve o grafo compilado. |
| `studio.py` | Expõe o grafo ao servidor: `grafo = construir()`. |
| `langgraph.json` | Diz ao servidor onde está o grafo e qual `.env` carregar. |
| `langgraph dev` | Sobe a API local em `http://127.0.0.1:2024` (estado em memória e em `.langgraph_api/`). |
| Studio (web) | Interface em `smith.langchain.com/studio` para rodar o grafo, ver cada nó e retomar pausas. |

Dois caminhos de execução existem lado a lado e **não compartilham estado**:

- `python etapa07_grafo.py ...` usa o `SqliteSaver` em `saidas/checkpoints.db`.
- `langgraph dev` usa a persistência própria do servidor, em `.langgraph_api/`.

Uma execução pausada em um não aparece no outro.

## 2. Implementar a integração

A CLI já vem no `.venv` (`langgraph-cli[inmem]`). Se precisar instalar:

```bash
uv pip install -U "langgraph-cli[inmem]"      # o .venv é do uv e não tem pip
```

### 2.1 `studio.py`

```python
"""Expõe o grafo compilado para o `langgraph dev` (LangGraph Studio). O servidor traz o checkpointer dele."""
from etapa07_grafo import construir

grafo = construir()
```

Não passe o `SqliteSaver` aqui: o servidor de desenvolvimento fornece o checkpointer e rejeita um próprio.

### 2.2 `langgraph.json`

```json
{
  "dependencies": ["."],
  "graphs": { "rh": "./studio.py:grafo" },
  "env": ".env"
}
```

- `rh` é o nome do grafo (o `assistant_id` nas chamadas à API e a escolha no Studio).
- `./studio.py:grafo` é `arquivo:variável`.
- `env` carrega o `.env` (incluindo `OPENAI_API_KEY` e `TOKEN_REGISTRO`).

## 3. Subir o servidor

Na pasta `avaliacao/`:

```bash
.venv/bin/langgraph dev                 # abre o navegador no Studio
.venv/bin/langgraph dev --no-browser    # só sobe o servidor
.venv/bin/langgraph dev --port 2025     # se a 2024 estiver ocupada
```

Sinais de que subiu: `Application started up` no log e a resposta de `curl localhost:2024/ok`:

```json
{"ok":true,"services":{}}
```

O servidor recarrega sozinho quando você edita os arquivos.

## 4. Usar o Studio web

1. Coloque a chave do LangSmith no `.env`:
   ```
   LANGSMITH_API_KEY=lsv2_...
   LANGSMITH_TRACING=true        # opcional: grava os traces (prompts e respostas vão para o LangSmith)
   LANGSMITH_PROJECT=rh-grafo    # opcional
   ```
2. Suba o `langgraph dev`. Se o navegador não abrir, acesse:
   `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`
3. Entre na conta do LangSmith, escolha o grafo `rh` e informe a entrada:
   ```json
   {"thread_id": "C2", "texto": "Matrícula 1002. Quero tirar férias de 12/04/2027 a 26/04/2027 e vender 10 dias."}
   ```
4. Quando o grafo pausar em `aprovacao_chefia`, retome enviando:
   ```json
   {"aprovado": true, "aprovador": "1010", "motivo": ""}
   ```
   Para rejeitar: `{"aprovado": false, "aprovador": "1010", "motivo": "confirme o valor da venda"}`.

Se o Studio não conectar:

- Safari e Brave bloqueiam uma página `https` falando com `http://127.0.0.1`. Use Chrome ou Firefox.
- Ou suba com túnel: `.venv/bin/langgraph dev --tunnel`. O tráfego passa por um endereço público temporário; evite com dados reais.

## 5. Testar a integração sem o Studio (API local)

Com o servidor no ar, o fluxo completo do C2 (pausa e retomada) pela API:

```bash
# 1) cria a thread
T=$(curl -s -X POST localhost:2024/threads -H 'content-type: application/json' -d '{}' \
    | python3 -c 'import sys,json;print(json.load(sys.stdin)["thread_id"])')

# 2) roda até a pausa da chefia
curl -s -X POST localhost:2024/threads/$T/runs/wait -H 'content-type: application/json' \
  -d '{"assistant_id":"rh","input":{"thread_id":"api-C2","texto":"Matrícula 1002. Quero tirar férias de 12/04/2027 a 26/04/2027 e vender 10 dias."}}'

# 3) retoma com a decisão da chefia
curl -s -X POST localhost:2024/threads/$T/runs/wait -H 'content-type: application/json' \
  -d '{"assistant_id":"rh","command":{"resume":{"aprovado":true,"aprovador":"1010","motivo":""}}}'
```

O resultado esperado:

| Passo | Resposta |
|---|---|
| 2 | `caminho` terminando em `validar` e `__interrupt__` com `"pergunta": "Aprova o despacho?"` e `"chefia": "1010"` |
| 3 | `"resultado": "registrado"` e `"protocolo": "b7b6f485"` |

Outros casos úteis:

| Caso | O que esperar |
|---|---|
| C1 (abono) | não pausa; termina em `registrar` com o protocolo `ae788d33` |
| C3, C4, C7 | `recusar` (bloqueado na entrada) |
| C5 | `pedir_dados` |
| C6 | termina em `registrar` com decisão `indeferido` (protocolo `6f1b47d7`) |

A documentação interativa da API fica em `http://127.0.0.1:2024/docs`.

## 6. Testar o grafo sem servidor

Estes comandos não dependem do `langgraph dev`:

```bash
python conferir.py 7 8 9 --opcionais     # sem LLM: o grafo com respostas fixas
python conferir.py --llm                 # com o LLM de verdade
python etapa07_grafo.py --todos          # os 12 casos
python etapa07_grafo.py --mermaid        # o diagrama do grafo
```

## 7. Cuidados

- **Registros duplicados:** o MCP grava em `saidas/registros.json` pelos dois caminhos. Rodar o mesmo caso nos dois
  devolve `duplicado` (idempotência), não um novo registro.
- **Limpeza:** `saidas/` (registros, auditoria, checkpoints) e `.langgraph_api/` são artefatos de teste. Apague-os entre
  rodadas se quiser um estado limpo; o `conferir.py` também limpa o que grava.
- **Segredos:** `.env` contém `OPENAI_API_KEY`, `LANGSMITH_API_KEY` e `TOKEN_REGISTRO`. Não os versione nem os cole em
  conversas ou logs.
- **Privacidade:** com `LANGSMITH_TRACING=true`, prompts e respostas vão para o LangSmith. Os casos do exercício são
  fictícios; com dados reais de servidores, deixe o tracing desligado.
- **Mudou o grafo?** O servidor recarrega sozinho. Se mudar `langgraph.json` (por exemplo, o nome do grafo), reinicie o
  `langgraph dev`.
