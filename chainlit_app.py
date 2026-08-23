# Importa o Chainlit, responsável pela interface de chat.
import chainlit as cl

# Representa uma mensagem enviada por uma pessoa no padrão LangChain.
from langchain_core.messages import HumanMessage

# Importa a função que constrói e compila nosso grafo LangGraph.
from anomaly_companion_agent.graph import create_graph


# O grafo é criado uma vez, quando a aplicação Chainlit inicia.
# Ele será reutilizado sempre que o usuário enviar uma mensagem.
graph = create_graph()


# Este decorator registra uma função para o evento:
# "uma nova conversa foi iniciada".
@cl.on_chat_start
async def on_chat_start():
    """Executa quando o usuário abre uma nova conversa."""

    # Cria uma mensagem do assistente e a envia para a interface.
    await cl.Message(
        content=(
            "Olá! Sou o Anomaly Companion. "
            "Informe uma anomalia para investigação."
        )
    ).send()


# Este decorator registra uma função para o evento:
# "o usuário enviou uma mensagem".
@cl.on_message
async def on_message(message: cl.Message):
    """Recebe uma mensagem e a envia para o LangGraph."""

    # Constrói o estado inicial esperado pelo MessagesState.
    #
    # message.content contém somente o texto digitado
    # pelo usuário na interface do Chainlit.
    initial_state = {
        "messages": [
            HumanMessage(content=message.content)
        ]
    }

    # O callback permite que o Chainlit acompanhe a execução
    # do LangGraph, incluindo chamadas do modelo e das tools.
    execution_config = {
        "callbacks": [
            cl.LangchainCallbackHandler()
        ]
    }

    # Executa o grafo de forma assíncrona.
    #
    # O fluxo poderá ser:
    # assistant → tools → assistant → END
    #
    # O resultado é o estado completo ao final da execução.
    result = await graph.ainvoke(
        initial_state,
        config=execution_config,
    )

    # O MessagesState acumula todas as mensagens da execução.
    # A última mensagem é a resposta final produzida pelo agente.
    final_message = result["messages"][-1]

    # Apresenta o conteúdo da resposta na interface do Chainlit.
    await cl.Message(
        content=final_message.content
    ).send()