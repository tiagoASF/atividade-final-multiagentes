"""
ETAPA 10 -- Observabilidade (15 min): onde o tempo foi gasto e quanto custou, por nó do grafo.

ESQUELETO:
  ETAPA 10.2 -- medido(): embrulha um nó, mede o tempo e grava uma linha em saidas/metricas.jsonl
  ETAPA 10.3 -- resumo(): nós percorridos, tempo total, nó mais lento e tokens totais de uma execução
  (ETAPA 10.1 fica em etapa10_governanca.py: o hook do 🆕 B ganha um segundo papel, registrar)

Até você fazer a 10.2, medido() devolve o nó sem mudar nada: o grafo funciona igual.

REFERÊNCIAS NAS AULAS
  aula5/exemplos/11_observabilidade/agente_observavel.py        ler o que aconteceu numa execução (result.new_items)
  aula3/agente_hook2.py, aula3/agente_hook3.py                  RunHooks para enxergar o loop do agente
  aula8/exemplos/03_observabilidade/1_codigo_pronto/passo1_trace.py   trace e spans (o Langfuse do passo 2 é opcional)

Rodar:
    python etapa10_observabilidade.py <thread_id>     # imprime o resumo de uma execução já feita
"""
import functools
import json
import sys
import time

from dados_rh import SAIDAS

ARQUIVO_METRICAS = SAIDAS / "metricas.jsonl"


def medido(nome: str, no):
    # ETAPA 10.2 -- devolva uma função que:
    #   1. mede o tempo de no(estado) com time.perf_counter();
    #   2. grava em ARQUIVO_METRICAS uma linha JSON com: thread_id (estado.get("thread_id")), no, segundos,
    #      e, se o nó devolveu, "tokens" e "fonte_feriados";
    #   3. devolve o MESMO dicionário que o nó devolveu.
    #   Use @functools.wraps(no) para o nome do nó continuar o mesmo.
    @functools.wraps(no)
    def embrulhado(estado):
        inicio = time.perf_counter()
        saida = no(estado)
        linha = {"thread_id": estado.get("thread_id"), "no": nome,
                 "segundos": round(time.perf_counter() - inicio, 3)}
        for chave in ("tokens", "fonte_feriados"):
            if chave in saida:
                linha[chave] = saida[chave]
        with open(ARQUIVO_METRICAS, "a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(linha, ensure_ascii=False) + "\n")
        return saida

    return embrulhado


def resumo(thread_id: str) -> dict:
    # ETAPA 10.3 -- leia ARQUIVO_METRICAS, filtre pelo thread_id e devolva
    #   {"nos": [...], "segundos_total": ..., "mais_lento": (no, segundos), "tokens_total": ...}
    linhas = []
    if ARQUIVO_METRICAS.exists():
        for texto in ARQUIVO_METRICAS.read_text(encoding="utf-8").splitlines():
            linha = json.loads(texto)
            if linha["thread_id"] == thread_id:
                linhas.append(linha)
    mais_lento = max(linhas, key=lambda l: l["segundos"], default=None)
    return {"nos": [l["no"] for l in linhas],
            "segundos_total": round(sum(l["segundos"] for l in linhas), 3),
            "mais_lento": (mais_lento["no"], mais_lento["segundos"]) if mais_lento else None,
            "tokens_total": sum(l.get("tokens", 0) for l in linhas)}


if __name__ == "__main__":
    print(json.dumps(resumo(sys.argv[1]), ensure_ascii=False, indent=2))
