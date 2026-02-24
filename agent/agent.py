import asyncio
import operator
from typing import Literal

from langchain.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from typing_extensions import Annotated, TypedDict


class MessagesState(TypedDict):
    # new messages automatically get appended using `add`
    messages: Annotated[list[AnyMessage], operator.add]


def route_llm_response(state: MessagesState) -> Literal["tool_node", END]:
    last_message = state["messages"][-1]

    # if this assert fails, we are using this check for a node that returns something besides an AIMessage
    # (currently only used after `llm_node`)
    assert isinstance(last_message, AIMessage)

    # if the model wants to use a tool call, transition to the tool_node
    if last_message.tool_calls:
        return "tool_node"

    # otherwise, return to the user
    return END


model = ChatOllama(
    model="gpt-oss:120b",
)

client = MultiServerMCPClient(
    {
        "gdc": {
            "url": "http://localhost:8000/sse",
            "transport": "sse",
        }
    }
)


async def make_graph():
    tools = await client.get_tools()
    tools_by_name = {tool.name: tool for tool in tools}
    model_with_tools = model.bind_tools(tools)

    def llm_node(state: MessagesState) -> MessagesState:
        return {
            "messages": [
                model_with_tools.invoke(
                    [
                        SystemMessage(
                            content="You are a helpful bioinformatics assistant with access to specialized tools to query information about genetic mutations using the Genomic Data Commons (GDC). Use the tools to answer questions. Multiple chained tool calls may be required to answer a question."
                        )
                    ]
                    + state["messages"]
                )
            ],
        }

    async def tool_node(state: MessagesState) -> MessagesState:
        last_message = state["messages"][-1]

        # if this assert fails, we transitioned to `tool_node` following some non-AIMessage or the tools are empty
        # (currently this is not possible using the `route_llm_response` conditional)
        assert isinstance(last_message, AIMessage)
        assert last_message.tool_calls

        tool_results = []
        for tool_call in last_message.tool_calls:
            tool = tools_by_name[tool_call["name"]]
            observation = await tool.ainvoke(tool_call["args"])
            tool_results.append(
                ToolMessage(content=observation, tool_call_id=tool_call["id"])
            )
        return {"messages": tool_results}

    graph = StateGraph(MessagesState)
    graph.add_node("llm_node", llm_node)
    graph.add_node("tool_node", tool_node)

    # state transitions
    graph.add_edge(START, "llm_node")
    graph.add_conditional_edges("llm_node", route_llm_response)
    graph.add_edge("tool_node", "llm_node")

    agent = graph.compile()

    # if serving the agent via langgraph-cli, use the `make_graph` function as the entrypoint
    return agent


async def main():
    agent = await make_graph()
    messages = await agent.ainvoke(
        MessagesState(
            messages=[HumanMessage(content="How many cases of SSM in BRAF are there?")]
        )
    )
    for m in messages["messages"]:
        m.pretty_print()


if __name__ == "__main__":
    asyncio.run(main())
