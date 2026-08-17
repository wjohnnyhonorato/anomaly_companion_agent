from functools import partial

from langchain_core.messages import SystemMessage
from langgraph.graph import MessagesState, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from anomaly_companion_agent.model import create_model
from anomaly_companion_agent.tools import TOOLS


SYSTEM_PROMPT = """
Você é o Anomaly Companion, um assistente para troubleshooting
e RCA de anomalias em ambientes de microserviços.

Use as ferramentas disponíveis para consultar evidências dos modelos.
Não invente informações.

Resultados de RCA representam candidatos causais produzidos
pelo modelo e não causas definitivamente comprovadas.
"""


def llm_node(state: MessagesState, *, model) -> dict:
    """
    Executa o nó do LLM usando o estado atual do grafo.

    Parameters
    ----------
    state : MessagesState
        Estado compartilhado do LangGraph. Neste MVP ele contém
        o histórico em ``state["messages"]``.
    model
        Chat model já configurado e com as tools vinculadas.

    Returns
    -------
    dict
        Atualização parcial do estado contendo a nova mensagem
        produzida pelo LLM.

    Notes
    -----
    Um node de ``StateGraph`` lê o estado e devolve somente
    aquilo que deseja atualizar. ``MessagesState`` sabe acumular
    as novas mensagens no histórico.
    """
    response = model.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            *state["messages"],
        ]
    )

    return {
        "messages": [response]
    }


def create_graph():
    """
    Constrói e compila o grafo do Anomaly Companion.

    Fluxo
    -----
    START -> assistant
                |
          tools_condition
             /      \
          tools      END
            |
            +------> assistant

    Returns
    -------
    CompiledStateGraph
        Grafo pronto para receber ``invoke``.

    Notes
    -----
    - ``StateGraph(MessagesState)`` define o tipo de estado
      compartilhado pelos nodes.
    - ``assistant`` chama o LLM.
    - ``tools`` é um único ``ToolNode`` capaz de executar
      qualquer tool presente em ``TOOLS``.
    - ``tools_condition`` verifica se a última resposta do LLM
      contém tool calls. Se houver, segue para ``tools``;
      caso contrário, encerra o grafo.
    """
    model = create_model()

    # O provider é criado em model.py. Aqui o agente decide
    # quais tools estarão disponíveis ao LLM.
    model_with_tools = model.bind_tools(TOOLS)

    builder = StateGraph(MessagesState)

    # ``llm_node`` foi escrito para receber state e model.
    # ``partial`` fixa o model agora, deixando para o LangGraph
    # uma função que precisa receber somente o state.
    assistant_node = partial(
        llm_node,
        model=model_with_tools,
    )

    builder.add_node(
        "assistant",
        assistant_node,
    )

    # Um único ToolNode pode executar qualquer tool registrada
    # na lista TOOLS, conforme a tool call produzida pelo LLM.
    builder.add_node(
        "tools",
        ToolNode(TOOLS),
    )

    builder.add_edge(
        START,
        "assistant",
    )

    builder.add_conditional_edges(
        "assistant",
        tools_condition,
    )

    builder.add_edge(
        "tools",
        "assistant",
    )

    return builder.compile()
