from langchain_core.messages import HumanMessage

from anomaly_companion_agent.graph import create_graph


def run_anomaly_companion(graph, user_question: str) -> str:
    """
    Executa uma pergunta no Anomaly Companion.

    Parameters
    ----------
    graph
        Grafo LangGraph já compilado.
    user_question : str
        Pergunta feita pelo SRE.

    Returns
    -------
    str
        Texto da resposta final produzida pelo agente.

    Notes
    -----
    ``graph.invoke`` recebe o estado inicial do grafo. Neste MVP,
    o estado contém somente ``messages``.
    """
    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content=user_question)
            ]
        }
    )

    final_message = result["messages"][-1]
    return final_message.text


def save_graph(
    graph,
    output_path: str = "anomaly_companion_graph.png",
) -> None:
    """
    Salva uma representação visual do grafo em PNG.

    Parameters
    ----------
    graph
        Grafo LangGraph já compilado.
    output_path : str
        Caminho do arquivo PNG de saída.
    """
    graph.get_graph().draw_mermaid_png(
        output_file_path=output_path
    )


def main() -> None:
    """
    Ponto de entrada local do projeto.

    Cria o grafo, salva sua visualização, executa uma pergunta
    de teste e imprime a resposta do Anomaly Companion.
    """
    graph = create_graph()

    save_graph(graph)

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
