import os
from pyexpat import model

from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

from IPython.display import Image, display


# # # modelo mental de um agente basico

# 1. STATE
#    O que precisa circular entre as etapas?

# 2. CAPACIDADES
#    Quais modelos, tools, APIs ou funções eu tenho?

# 3. NODES
#    Quais são as etapas de processamento?

# 4. EDGES
#    Como essas etapas se conectam?
#    Existem decisões/loops?

# 5. COMPILE
#    Transformo a definição em um grafo executável.

# 6. INVOKE
#    Entrego o estado inicial e rodo.


# ============================================================
# CONFIGURAÇÃO
# ============================================================

MODEL_NAME = "gemini-3.5-flash"

SYSTEM_PROMPT = """
Você é o Anomaly Companion, um assistente para troubleshooting
e RCA de anomalias em ambientes de microserviços.

Use as ferramentas disponíveis para consultar evidências dos modelos.
Não invente informações.

Resultados de RCA representam candidatos causais produzidos
pelo modelo e não causas definitivamente comprovadas.
"""


# ============================================================
# TOOL
# ============================================================

@tool
def get_rca(anomaly_id: str) -> dict:
    """
    Consulta o resultado do modelo RCA para uma anomalia.

    Parameters
    ----------
    anomaly_id : str
        Identificador da anomalia.
        Exemplo: ARGOS-123.

    Returns
    -------
    dict
        Candidatos causais identificados pelo modelo RCA
        e suas respectivas contribuições.
    """

    return {
        "anomaly_id": anomaly_id,
        "root_cause_candidates": [
            {
                "service": "payment-service",
                "causal_contribution": 0.42,
            },
            {
                "service": "redis-service",
                "causal_contribution": 0.31,
            },
        ],
    }


TOOLS = [get_rca]


# ============================================================
# MODELO
# ============================================================

def create_model():
    """
    Cria o modelo utilizado pelo Anomaly Companion.

    Returns
    -------
    ChatOpenAI
        Modelo configurado usando a API Gemini
        compatível com o padrão OpenAI.

    Raises
    ------
    RuntimeError
        Caso GEMINI_API_KEY não seja encontrada.
    """

    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY não encontrada no .env"
        )


    model = ChatGoogleGenerativeAI(
    model=MODEL_NAME,
    api_key=api_key,
)

    return model.bind_tools(TOOLS) # bind_tools vincula tools no mmodelo instanciado


# ============================================================
# NÓ DO LLM
# ============================================================

def create_llm_node(model):
    """
    Cria o nó responsável pelas decisões do LLM.

    Parameters
    ----------
    model
        Modelo com as tools disponíveis.

    Returns
    -------
    callable
        Função que recebe o estado atual do grafo e retorna
        uma nova mensagem produzida pelo LLM.
    """

    def llm_node(state: MessagesState):
        """
        Executa uma chamada ao LLM usando o estado atual.

        Parameters
        ----------
        state : MessagesState
            Estado do LangGraph contendo o histórico
            de mensagens.

        Returns
        -------
        dict
            Nova mensagem produzida pelo modelo.
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

    return llm_node


# ============================================================
# GRAFO
# ============================================================

def create_graph():
    """
    Constrói o grafo do Anomaly Companion.

    Fluxo:

        START
          |
          v
         LLM
        /   \
     tool?   não
      |       |
      v       END
    TOOLS
      |
      v
     LLM

    Returns
    -------
    CompiledStateGraph
        Grafo compilado e pronto para execução.
    """

    model = create_model()

    llm_node = create_llm_node(model)

    builder = StateGraph(MessagesState)

    # Nó responsável pelo raciocínio/decisão do LLM.
    builder.add_node(
        "assistant", # nome do nó
        llm_node, # o que o nó faz
    )

    # Nó responsável pela execução das tools.
    builder.add_node(
        "tools", # nome do nó
        ToolNode(TOOLS), # o que o nó faz, neste caso uma função interna que executa as tools disponíveis
    )

    # Entrada do grafo.
    builder.add_edge(
        START,
        "assistant",
    )

    # Decide:
    #
    # assistant → tools
    # ou
    # assistant → END
    builder.add_conditional_edges(
        "assistant",
        tools_condition,
    )

    # Depois da tool, retorna ao LLM.
    builder.add_edge(
        "tools",
        "assistant",
    )

    return builder.compile()


# ============================================================
# EXECUÇÃO
# ============================================================

def run_anomaly_companion(
    graph,
    user_question: str,
) -> str:
    """
    Executa uma pergunta no Anomaly Companion.

    Parameters
    ----------
    graph
        Grafo compilado do LangGraph.

    user_question : str
        Pergunta realizada pelo SRE.

    Returns
    -------
    str
        Resposta final produzida pelo agente.
    """

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content=user_question
                )
            ]
        }
    )

    final_message = result["messages"][-1]

    return final_message.text


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """
    Executa localmente o Anomaly Companion.
    """

    graph = create_graph()

    # Salva o grafo como imagem
    graph.get_graph().draw_mermaid_png(
        output_file_path="anomaly_companion_graph.png"
    )

    question = (
        "Qual é a principal causa "
        "da anomalia ARGOS-123?"
    )

    answer = run_anomaly_companion(
        graph=graph,
        user_question=question,
    )

    print("\nAnomaly Companion:")
    print(answer)


if __name__ == "__main__":
    main()