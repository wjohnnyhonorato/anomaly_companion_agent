# Anomaly Companion

MVP de uma camada agêntica para apoiar troubleshooting de anomalias em ambientes de microsserviços.

O projeto usa **LangGraph** para orquestração do agente e mantém a arquitetura desacoplada do provider de LLM. No ambiente local, o MVP usa Gemini por meio do adapter `ChatGoogleGenerativeAI`, mas o grafo foi estruturado para que a troca de provider afete principalmente a camada de modelo, e não a lógica do agente.

---

## 1. Contexto do projeto

O pipeline de observabilidade produz um **Anomaly Card** a partir de diferentes modelos e fontes de contexto operacional.

Conceitualmente:

```text
Argos TS
   ↓
Argos Bad Traces
   ↓
RCA causal
   ↓
Causal spans
   ↓
Knowledge Graph
   ↓
Recursos / ARNs
   ↓
POEs
   ↓
Anomaly Card
```

### Objetivo do Anomaly Card

O Anomaly Card não deve funcionar como um dashboard cheio de métricas.

Seu objetivo é ser uma **interface rápida de apoio à decisão para SREs e responsáveis por produtos de tecnologia**, reunindo apenas as evidências mais úteis para responder perguntas como:

- O que aconteceu?
- Onde a anomalia está concentrada?
- Quais são os principais candidatos causais?
- Quais spans estão relacionados ao possível problema?
- Quais recursos de infraestrutura estão associados?
- Existe um procedimento operacional aplicável?

O card consolida resultados já produzidos por modelos especializados.

---

## 2. Papel do Anomaly Companion

O **Anomaly Companion** é a camada agêntica construída sobre esse contexto.

Enquanto o Anomaly Card apresenta evidências estruturadas, o Anomaly Companion permite ao SRE conversar com essas evidências.

Exemplo:

```text
SRE:
"Qual é a principal causa da anomalia ARGOS-123?"

        ↓

Anomaly Companion

        ↓

LLM decide consultar get_rca()

        ↓

Tool retorna candidatos causais

        ↓

LLM interpreta a evidência

        ↓

Resposta para o SRE
```

A ideia é evitar enviar um contexto enorme e indiscriminado para o LLM.

Em vez disso, o agente consulta **capacidades específicas sob demanda**, como:

```text
get_rca()
get_causal_spans()
get_related_resources()
get_poe()
```

No MVP atual existe somente `get_rca()`.

---

# 3. Estrutura atual

```text
anomaly_companion_agent/
├── .gitignore
├── .python-version
├── anomaly_companion_graph.png
├── main.py
├── pyproject.toml
├── README.md
├── src/
│   └── anomaly_companion_agent/
│       ├── __init__.py
│       ├── graph.py
│       ├── model.py
│       └── tools.py
└── uv.lock
```

A divisão busca manter responsabilidades simples e explícitas.

---

# 4. `model.py`

Responsável pela **instanciação do modelo de linguagem**.

Hoje:

```text
LangChain
   ↓
ChatGoogleGenerativeAI
   ↓
Gemini
```

A função principal é:

```python
create_model()
```

Ela:

1. carrega a variável `GEMINI_API_KEY`;
2. cria o adapter do provider;
3. devolve um chat model pronto para uso.

Exemplo conceitual:

```python
model = create_model()
```

## Por que separar o modelo?

Para que o restante da aplicação não dependa diretamente do provider.

Hoje:

```python
ChatGoogleGenerativeAI(...)
```

No futuro, por exemplo:

```python
ChatOpenAI(...)
```

ou um adapter compatível com o gateway corporativo.

A intenção arquitetural é:

```text
Provider específico
        ↓
Adapter LangChain
        ↓
Interface comum
        ↓
LangGraph
```

Assim, a troca do provider não deveria exigir uma reconstrução do grafo.

A qualidade e as capacidades do novo modelo ainda precisam ser validadas, mas a **arquitetura de orquestração deve permanecer estável**.

---

# 5. `tools.py`

Contém as capacidades que o agente pode utilizar.

No MVP:

```python
@tool
def get_rca(anomaly_id: str) -> dict:
    ...
```

O decorator:

```python
@tool
```

transforma uma função Python em uma Tool compatível com LangChain.

A partir de:

- nome da função;
- type hints;
- docstring;

o LangChain consegue construir a descrição da ferramenta apresentada ao LLM.

Também existe:

```python
TOOLS = [
    get_rca,
]
```

Essa lista representa o conjunto de tools disponibilizadas ao agente.

Conceitualmente:

```text
TOOLS
  ├── get_rca
  ├── get_causal_spans      # futuro
  ├── get_related_resources # futuro
  └── get_poe               # futuro
```

### Tool não é Node

Uma distinção importante:

```text
Tool
=
capacidade que pode ser escolhida pelo LLM
```

enquanto:

```text
Node
=
etapa do workflow do LangGraph
```

`get_rca()` é uma Tool.

Ela não aparece como um node separado no grafo atual.

---

# 6. `graph.py`

É onde fica a **orquestração LangGraph**.

Ele reúne:

- State;
- Nodes;
- Edges;
- roteamento;
- compilação do grafo.

O fluxo atual é:

```text
          ┌───────────────┐
          │   assistant   │
          └───────┬───────┘
                  │
          tools_condition
             /          \
            /            \
           ▼              ▼
        tools            END
           │
           └─────────► assistant
```

---

## `StateGraph(MessagesState)`

A linha:

```python
builder = StateGraph(MessagesState)
```

cria um grafo cujo estado compartilhado segue o schema `MessagesState`.

Neste MVP, o principal estado é:

```python
state["messages"]
```

Esse histórico acumula mensagens como:

```text
HumanMessage
     ↓
AIMessage pedindo uma tool
     ↓
ToolMessage com o resultado
     ↓
AIMessage com a resposta final
```

Mais adiante, o estado poderá ser enriquecido.

Exemplo:

```python
class AnomalyState(MessagesState):
    anomaly_id: str
    severity: str
    selected_service: str
```

---

## Node `assistant`

O node:

```text
assistant
```

executa o LLM.

Sua função recebe o estado atual:

```python
llm_node(state, model)
```

e devolve uma atualização parcial:

```python
{
    "messages": [response]
}
```

Conceitualmente:

```text
State
  ↓
assistant
  ↓
LLM
  ↓
nova mensagem
  ↓
State atualizado
```

---

## Node `tools`

O node:

```text
tools
```

é criado por:

```python
ToolNode(TOOLS)
```

Um único `ToolNode` pode executar qualquer tool registrada em `TOOLS`.

Exemplo:

```text
                 ToolNode
                 /   |   \
                /    |    \
               ▼     ▼     ▼
          get_rca  get_poe get_spans
```

Quem escolhe qual tool deve ser usada é o **LLM**.

O `ToolNode` apenas executa a tool solicitada.

---

## `tools_condition`

O roteamento:

```python
builder.add_conditional_edges(
    "assistant",
    tools_condition,
)
```

pergunta:

> A última mensagem produzida pelo LLM contém uma chamada de tool?

Se sim:

```text
assistant → tools
```

Se não:

```text
assistant → END
```

Portanto:

```text
LLM
→ escolhe qual tool chamar

tools_condition
→ decide se é necessário ir para o ToolNode

ToolNode
→ executa a tool escolhida
```

---

## `partial`

O `llm_node` foi escrito de forma explícita:

```python
def llm_node(state, *, model):
```

Mas o LangGraph deve receber um node que, durante a execução, receba principalmente o `state`.

Por isso usamos:

```python
assistant_node = partial(
    llm_node,
    model=model_with_tools,
)
```

O `partial` fixa antecipadamente o argumento `model`.

Assim:

```text
antes

llm_node(state, model)
```

vira, para o grafo:

```text
assistant_node(state)
```

Isso evita esconder a dependência do modelo dentro de uma função aninhada e deixa o fluxo mais fácil de estudar.

---

# 7. `main.py`

É a camada de entrada da aplicação.

Ele não define a lógica do agente.

Sua responsabilidade é:

```text
criar o grafo
     ↓
montar estado inicial
     ↓
graph.invoke(...)
     ↓
obter resposta
     ↓
apresentar ao usuário
```

A função:

```python
run_anomaly_companion(...)
```

recebe:

- o grafo compilado;
- a pergunta do SRE.

Depois executa:

```python
graph.invoke(...)
```

O `invoke` entrega o **estado inicial** ao LangGraph e dispara o workflow.

Neste MVP:

```python
{
    "messages": [
        HumanMessage(...)
    ]
}
```

---

# 8. Modelo mental geral para LangGraph

O modelo mental usado neste projeto é propositalmente mais genérico do que "criar um agente com LLM".

## 1. STATE

Pergunta:

> O que precisa circular entre as etapas?

Exemplo:

```text
messages
anomaly_id
severity
selected_service
```

---

## 2. CAPACIDADES

Pergunta:

> O que o sistema consegue usar?

Exemplos:

```text
LLM
Tools
APIs
modelos de ML
MCP
bancos
Knowledge Graph
```

Essas capacidades não são necessariamente nodes.

---

## 3. NODES

Pergunta:

> Quais são as etapas de processamento?

Um node pode executar:

```text
LLM
Python
regra
API
ToolNode
subgraph
```

Um node é, conceitualmente:

```text
State
  ↓
processamento
  ↓
Partial State
```

---

## 4. EDGES

Pergunta:

> Como os nodes se conectam?

Podem existir:

```text
arestas normais
arestas condicionais
loops
branches
```

É aqui que a lógica de orquestração aparece.

---

## 5. COMPILE

Depois de definir:

```text
State
+
Nodes
+
Edges
```

o grafo é compilado:

```python
graph = builder.compile()
```

Antes disso existe apenas uma definição do workflow.

Depois do `compile`, existe um grafo executável.

---

## 6. INVOKE

Finalmente fornecemos o estado inicial:

```python
graph.invoke(initial_state)
```

Isso inicia a execução do workflow.

---

# 9. Regra mental resumida

Para qualquer novo projeto LangGraph:

```text
1. STATE
   O que circula?

2. CAPACIDADES
   O que posso usar?

3. NODES
   Quais etapas existem?

4. EDGES
   Como elas se conectam?

5. COMPILE
   Transformar a definição em workflow executável.

6. INVOKE
   Entregar estado inicial e executar.
```

A essência pode ser resumida como:

```text
LangGraph = State + Nodes + Edges
```

LLMs, tools, APIs e modelos de ML são capacidades utilizadas por esses nodes.

---

# 10. Fluxo completo do MVP atual

Para a pergunta:

```text
"Qual é a principal causa da anomalia ARGOS-123?"
```

o fluxo é:

```text
HumanMessage
     ↓
assistant
     ↓
LLM analisa a pergunta
     ↓
LLM solicita get_rca(ARGOS-123)
     ↓
tools_condition
     ↓
ToolNode
     ↓
get_rca()
     ↓
resultado do RCA entra no MessagesState
     ↓
assistant
     ↓
LLM interpreta o resultado
     ↓
não solicita nova tool
     ↓
tools_condition
     ↓
END
```

Visualmente:

```text
__start__
     |
     v
 assistant
     |
     | pede get_rca
     v
   tools
     |
     | resultado RCA
     v
 assistant
     |
     | resposta final
     v
  __end__
```

---

# 11. Princípio de independência do provider

Um requisito arquitetural importante deste projeto é:

> A lógica de orquestração do Anomaly Companion deve ser independente do provider de LLM.

Idealmente:

```text
                    Anomaly Companion

                       LangGraph
                          |
             ┌────────────┼────────────┐
             |            |            |
           State        Nodes        Tools
                          |
                          v
                    model adapter
                    /     |      \
                   /      |       \
                  v       v        v
              Gemini   OpenAI   Gateway
```

A troca de provider deve exigir principalmente uma alteração em:

```text
model.py
```

e uma nova validação técnica e de qualidade.

Arquivos como:

```text
graph.py
tools.py
main.py
```

não deveriam depender de detalhes específicos de Gemini, OpenAI ou outro provider.

---

# 12. Estado atual do MVP

Atualmente o projeto prova o seguinte fluxo:

```text
SRE
 ↓
LangGraph
 ↓
LLM
 ↓
tool calling
 ↓
get_rca()
 ↓
resultado estruturado
 ↓
LLM
 ↓
resposta em linguagem natural
```

A implementação de `get_rca()` ainda usa dados mockados.

O foco atual não é representar todo o pipeline real, mas consolidar uma arquitetura simples, reproduzível e compreensível antes de adicionar novas capacidades.

---

# 13. Evolução esperada

Sem alterar o modelo mental básico, o projeto poderá evoluir para capacidades como:

```text
get_anomaly_summary()
get_bad_traces()
get_rca()
get_causal_spans()
get_related_resources()
get_poe()
query_operational_context()
```

Posteriormente essas tools também poderão ser disponibilizadas por um **MCP Server**, mantendo LangGraph como camada de orquestração.

Conceitualmente:

```text
LangGraph
    ↓
agent / subgraphs
    ↓
MCP Client
    ↓
Argos MCP Server
    ↓
modelos e sistemas reais
```

A intenção é que a complexidade cresça sem alterar o modelo mental fundamental:

```text
State
+
Nodes
+
Edges
```
