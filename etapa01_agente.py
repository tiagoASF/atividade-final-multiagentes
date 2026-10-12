"""
ETAPA 1 -- Primeiro agente com tool local (15 min).

ESQUELETO: implemente as etapas na ordem. Cada uma está marcada com um comentário e um
raise NotImplementedError: troque esse raise pelo código da etapa e rode o arquivo.
  ETAPA 1.1 -- a tool consultar_servidor (SEM o salário)
  ETAPA 1.2 -- o agente AtendenteRH com a tool
  ETAPA 1.3 -- duas perguntas: uma que precisa da tool e uma que não precisa

REFERÊNCIAS NAS AULAS
  aula1/segundo_agente.py                            Agent + @function_tool + Runner.run_sync (o básico)
  exercicios_resolvidos/aula4/ex10_function_tool.py  tool que consulta uma TABELA e devolve JSON  <- o mais parecido
  aula8/exemplos/02_agente_tool/main.py              o agente decide quando chamar a tool (e quando não)

Rodar (a partir de aula10/):
    python etapa01_agente.py

Pronto quando: a tool é chamada só na primeira pergunta (o print dentro dela prova).
"""
import json

from agents import Agent, Runner, function_tool

from dados_rh import carregar_servidores
from provedor import configurar

MODELO = configurar()


# ETAPA 1.1 -- a tool
#   - leia o cadastro com carregar_servidores() e procure a matrícula;
#   - devolva json.dumps(...) com nome, cargo, equipe, saldo_ferias_dias e abonos_restantes
#     (NUNCA o salario_base: ele é dado restrito, ver Etapas 5 e 9), ou "matrícula não encontrada";
#   - ponha um print("[tool] consultar_servidor", matricula) no começo, para provar quando ela roda;
#   - capriche na DOCSTRING (com Args:): é o que o LLM lê para decidir chamar a tool.
#   Referência: exercicios_resolvidos/aula4/ex10_function_tool.py (consultar_protocolo)
@function_tool
def consultar_servidor(matricula: str) -> str:
    """Consulta o cadastro de um servidor pela matrícula e devolve nome, cargo, equipe,
    saldo de férias (em dias) e abonos pecuniários restantes.

    Args:
        matricula: matrícula do servidor, ex.: "1002".
    """
    print("[tool] consultar_servidor", matricula)
    servidor = carregar_servidores().get(matricula)
    if servidor is None:
        return "matrícula não encontrada"
    return json.dumps({
        "nome": servidor["nome"],
        "cargo": servidor["cargo"],
        "equipe": servidor["equipe"],
        "saldo_ferias_dias": servidor["saldo_ferias_dias"],
        "abonos_restantes": servidor["abonos_restantes"],
    }, ensure_ascii=False)


def criar_atendente() -> Agent:
    # ETAPA 1.2 -- o agente
    #   Agent(name="AtendenteRH", instructions=..., tools=[consultar_servidor])
    #   Instruções: atende servidores, responde em português e de forma breve, usa a tool quando a pergunta
    #   for sobre os dados de UM servidor, e não inventa saldo de cabeça.
    #   Referência: aula1/segundo_agente.py
    return Agent(
        name="AtendenteRH",
        instructions=
            "Você atende servidores do setor de Recursos Humanos (RH). Responda em português e de forma breve. "
            "Quando a pergunta for sobre os dados de UM servidor, use a ferramenta "
            "consultar_servidor. Não invente saldo de cabeça.",
        tools=[consultar_servidor],
    )


def main() -> None:
    # ETAPA 1.3 -- rode as duas perguntas com Runner.run_sync e imprima resultado.final_output
    #   1) "Quantos dias de férias a matrícula 1002 ainda tem?"   (precisa da tool)
    #   2) "O que é abono pecuniário?"                            (não precisa)
    #   Referência: aula8/exemplos/02_agente_tool/main.py
    agente = criar_atendente()
    for pergunta in ["Quantos dias de férias a matrícula 1002 ainda tem?", "O que é abono pecuniário?"]:
        resultado = Runner.run_sync(agente, pergunta)
        print(f"\n[usuário] {pergunta}")
        print(f"[resposta] {resultado.final_output}\n")


if __name__ == "__main__":
    print(f"[modelo] {MODELO}\n")
    main()
