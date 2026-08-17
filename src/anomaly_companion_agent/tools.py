from langchain_core.tools import tool


@tool
def get_rca(anomaly_id: str) -> dict:
    """
    Consulta o resultado do modelo RCA para uma anomalia.

    Parameters
    ----------
    anomaly_id : str
        Identificador da anomalia.
        Exemplo: ``ARGOS-123``.

    Returns
    -------
    dict
        Candidatos causais identificados pelo modelo RCA e suas
        respectivas contribuições.

    Notes
    -----
    Neste MVP os dados são mockados. No produto real, o corpo
    desta função poderá consultar uma API, serviço de ML ou,
    futuramente, uma tool exposta via MCP.
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


# Catálogo de tools disponibilizadas ao agente neste grafo.
# Uma nova função Python decorada com @tool deve ser incluída
# aqui para ficar disponível ao modelo e ao ToolNode.
TOOLS = [
    get_rca,
]
