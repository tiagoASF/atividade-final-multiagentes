"""
ETAPA 6 -- Os especialistas, cada um com UMA responsabilidade e SÓ as tools de que precisa.

ESQUELETO:
  ETAPA 6.1 -- criar_normas(), criar_escala(), criar_financeiro(), criar_redator()
  ETAPA 6.2 -- criar_coordenador(): usa Normas, Escala e Financeiro como TOOLS (as_tool)

As tools abaixo (PRONTAS) só repassam a chamada ao MCP Server do RH (cliente_mcp.chamar_mcp_async). Dar a cada agente
só as tools dele é o PRIVILÉGIO MÍNIMO (Etapa 9.1); o hook do 🆕 B (etapa10_governanca.py) confere isso em tempo de execução.

REFERÊNCIAS NAS AULAS
  aula4/ex03_agente_as_tool.py                         Coordenador que chama especialistas como tools    <- o mais parecido
  aula2/agente_handoff2.py                             as_tool com tool_name e tool_description
  aula4/ex02_handoff_roteamento.py                     handoff: compare (quem responde no fim?)
  aula7/exemplos/02_agentes_especializados/main.py     uma responsabilidade por agente
  aula7/agentes.py                                     ModelSettings(temperature=0) para respostas mais estáveis
  aula8/exemplos/06_excessive_agency/1_codigo_pronto/main.py   o problema de dar tools DEMAIS a um agente
"""
import json

from agents import Agent, ModelSettings, RunHooks, function_tool

from etapa05_cliente_mcp import chamar_mcp_async
from etapa04_ferramentas import cotacao_usd_brl

CONFIG = ModelSettings(temperature=0)


# ------------------------------------------------------------------ tools (PRONTAS)
@function_tool
async def consultar_normas(tema: str) -> str:
    """Regras da norma interna sobre um tema: férias, prazos, escala, abono, diária, aprovação, saúde ou dados."""
    return json.dumps(await chamar_mcp_async("consultar_normas", {"tema": tema}), ensure_ascii=False)


@function_tool
async def consultar_escala(equipe: str, inicio: str, fim: str) -> str:
    """Afastamentos da equipe que se sobrepõem ao período (AAAA-MM-DD) e o limite de afastados da regra N5."""
    return json.dumps(await chamar_mcp_async("consultar_escala", {"equipe": equipe, "inicio": inicio, "fim": fim}),
                      ensure_ascii=False)


@function_tool
async def tabela_diarias(tipo_destino: str) -> str:
    """Moeda e valor da diária para o tipo de destino: capital, interior ou exterior."""
    return json.dumps(await chamar_mcp_async("tabela_diarias", {"tipo_destino": tipo_destino}), ensure_ascii=False)


@function_tool
async def consultar_remuneracao(matricula: str) -> str:
    """[RESTRITA] Salário-base de um servidor. Só para calcular a venda de férias (N2)."""
    print(f"[tool] consultar_remuneracao({matricula}) EXECUTOU")  # o 🆕 B prova que, barrada, ela NÃO executa
    return json.dumps(await chamar_mcp_async("consultar_remuneracao", {"matricula": matricula}), ensure_ascii=False)


@function_tool
def cotacao_dolar() -> str:
    """Cotação atual do dólar em reais (USD->BRL). Devolve 'indisponível' se a API falhar: nunca invente o câmbio."""
    cotacao = cotacao_usd_brl()
    return f"{cotacao:.4f}" if cotacao else "indisponível"


# ------------------------------------------------------------------ ETAPA 6.1: especialistas
def criar_normas() -> Agent:
    # ETAPA 6.1 -- Agent(name="Normas", instructions=..., tools=[consultar_normas], model_settings=CONFIG)
    #   Responsabilidade: dizer QUAIS regras se aplicam ao pedido e explicá-las em linguagem simples.
    #   NÃO calcula valores, NÃO consulta a escala. Recebe também as violações objetivas (etapa06_regras.py) para explicá-las.
    return Agent(
        name="Normas",
        instructions=(
            "Você é o especialista em normas internas do RH. Diga QUAIS regras (N1 a N10) se aplicam ao pedido "
            "e explique-as em linguagem simples, citando o código de cada uma. "
            "Use a ferramenta consultar_normas para ler o texto das regras; não cite regra de cabeça. "
            "Se receber violações objetivas, explique cada uma. "
            "Você NÃO julga se o pedido cumpre ou viola as regras (prazo, saldo, escala): isso já foi calculado pelo "
            "sistema e só vale o que vier em VIOLAÇÕES OBJETIVAS. Se não houver nenhuma, não aponte violação. "
            "Você NÃO calcula valores e NÃO consulta a escala."
        ),
        tools=[consultar_normas],
        model_settings=CONFIG,
    )


def criar_escala() -> Agent:
    # ETAPA 6.1 -- tools=[consultar_escala]. Confere a N5 e, se houver conflito, SUGERE outro período
    #   (com o mesmo número de dias, começando num dia permitido).
    return Agent(
        name="Escala",
        instructions=(
            "Você é o especialista em escala de afastamentos. Use a ferramenta consultar_escala para a equipe do "
            "servidor e confira a regra N5: o número de afastados no mesmo dia não pode passar do limite_afastados. "
            "Se houver conflito, SUGIRA outro período, com o mesmo número de dias e começando num dia permitido. "
            "Se não houver conflito, diga que a escala está livre. Não invente afastamentos."
        ),
        tools=[consultar_escala],
        model_settings=CONFIG,
    )


def criar_financeiro() -> Agent:
    # ETAPA 6.1 -- tools=[tabela_diarias, consultar_remuneracao, cotacao_dolar].
    #   Venda de férias (N2): dias_vendidos x salario_base / 30. Diárias (N7): uma por pernoite + meia no retorno;
    #   no exterior, em USD convertido pela cotação. Mostre a conta. Câmbio indisponível -> "a calcular".
    #   É o ÚNICO agente que vê o salário.
    return Agent(
        name="Financeiro",
        instructions=(
            "Você é o especialista em valores. Venda de férias (N2): dias_vendidos x salario_base / 30, "
            "com o salario_base vindo da ferramenta consultar_remuneracao. "
            "Diárias (N7): uma diária por dia com pernoite e meia diária no dia do retorno "
            "(ex.: ida em 8/6 e volta em 11/6 = 3 pernoites + meia = 3,5 diárias), com o valor vindo da "
            "ferramenta tabela_diarias; no exterior, o valor é em USD e deve ser convertido pela ferramenta "
            "cotacao_dolar. Mostre a conta passo a passo. "
            "Se o câmbio estiver indisponível, escreva 'a calcular' e nunca invente a cotação. "
            "Nunca escreva o salário-base na resposta, só o valor calculado."
        ),
        tools=[tabela_diarias, consultar_remuneracao, cotacao_dolar],
        model_settings=CONFIG,
    )


def criar_redator() -> Agent:
    # ETAPA 6.1 -- sem tools. Escreve o DESPACHO (deferimento ou indeferimento) usando SÓ os fatos recebidos:
    #   matrícula, período, decisão, regras citadas, valores e, no indeferimento, a sugestão de datas.
    #   Nunca escreve CPF nem dado de saúde (N10). Se receber um feedback (da validação ou da chefia), corrige.
    return Agent(
        name="Redator",
        instructions=(
            "Você escreve o DESPACHO do pedido (deferimento ou indeferimento), em português e de forma breve. "
            "Use SÓ os fatos recebidos: matrícula, período, decisão, regras citadas, valores e, no indeferimento, "
            "a sugestão de datas. Não invente nada. "
            "A DECISÃO recebida é definitiva: nunca a contradiga, e só cite como motivo as VIOLAÇÕES recebidas. "
            "Escreva as datas no formato DD/MM/AAAA (ex.: 09/04/2027), cite a matrícula e diga se o pedido foi "
            "DEFERIDO ou INDEFERIDO. "
            "Nunca escreva CPF, CID nem informação de saúde (N10). "
            "Se receber um feedback (da validação ou da chefia), corrija o despacho de acordo com ele."
        ),
        model_settings=CONFIG,
    )


# ------------------------------------------------------------------ ETAPA 6.2: coordenador
def criar_coordenador(hooks: RunHooks | None = None, tools_extras: list | None = None) -> Agent:
    # ETAPA 6.2 -- Agent(name="Coordenador", instructions=..., tools=[
    #       criar_normas().as_tool(tool_name="parecer_normas", tool_description=..., hooks=hooks,
    #                              failure_error_function=None),
    #       criar_escala().as_tool(tool_name="parecer_escala", ..., hooks=hooks, failure_error_function=None),
    #       criar_financeiro().as_tool(tool_name="parecer_financeiro", ..., hooks=hooks, failure_error_function=None),
    #       *(tools_extras or [])])
    #   O Coordenador decide QUAIS especialistas consultar (abono não precisa do Financeiro) e junta os pareceres.
    #   hooks=hooks nas as_tool faz o hook do 🆕 B enxergar também as tools DENTRO de cada especialista.
    #   failure_error_function=None: sem isso, um erro dentro do especialista (inclusive o bloqueio do 🆕 B) vira só
    #   um texto de erro para o Coordenador, que segue em frente. Com None, o erro interrompe a execução.
    #   tools_extras serve só para o teste do 🆕 B (dar de propósito consultar_remuneracao ao Coordenador).
    #   Referência: aula4/ex03_agente_as_tool.py
    return Agent(
        name="Coordenador",
        instructions=(
            "Você coordena a análise de um pedido de servidor. Consulte os especialistas necessários e junte os "
            "pareceres em um resumo único. Decida QUAIS consultar: parecer_normas para as regras (sempre); "
            "parecer_escala para férias e abono (conflito de equipe); parecer_financeiro SEMPRE que o pedido for "
            "de diária ou de férias com dias vendidos (dias_vendidos maior que zero), e NUNCA para abono ou "
            "férias sem venda. Chame cada especialista com os dados do pedido. "
            "Chame cada especialista repassando o pedido completo (tipo, matrícula, datas, dias vendidos, destino e "
            "tipo de destino), a data de HOJE e as VIOLAÇÕES OBJETIVAS (escreva 'nenhuma' quando não houver). As VIOLAÇÕES OBJETIVAS recebidas já foram calculadas pelo sistema e valem mais que "
            "qualquer opinião: se houver violações, o resumo deve dizer que o pedido NÃO pode ser deferido e citar "
            "cada uma; se não houver nenhuma, não aponte violação de prazo, saldo ou escala. "
            "Não invente nada além dos pareceres: não fale de diária num pedido de férias nem o contrário."
        ),
        tools=[
            criar_normas().as_tool(
                tool_name="parecer_normas",
                tool_description="Diz quais regras da norma interna se aplicam ao pedido e as explica.",
                hooks=hooks,
                failure_error_function=None,
            ),
            criar_escala().as_tool(
                tool_name="parecer_escala",
                tool_description="Confere o limite de afastados da equipe no período e sugere outro período se houver conflito.",
                hooks=hooks,
                failure_error_function=None,
            ),
            criar_financeiro().as_tool(
                tool_name="parecer_financeiro",
                tool_description="Calcula o valor da venda de férias ou das diárias, mostrando a conta.",
                hooks=hooks,
                failure_error_function=None,
            ),
            *(tools_extras or []),
        ],
        model_settings=CONFIG,
    )
