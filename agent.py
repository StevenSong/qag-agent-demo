import argparse
import asyncio

from langchain.agents import create_agent
from langchain.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama


async def main(query):
    model = ChatOllama(model="gpt-oss:120b", temperature=0, seed=42)
    mcp_client = MultiServerMCPClient(
        {
            "gdc": {
                "url": "http://localhost:8000/sse",
                "transport": "sse",
            }
        }
    )
    tools = await mcp_client.get_tools()
    agent = create_agent(model, tools)
    response = await agent.ainvoke(
        {
            "messages": [
                SystemMessage(
                    "You are a helpful bioinformatics assistant. Use the provided tools to answer genomics questions. You may need to perform multiple tool calls to arrive at the final answer."
                ),
                HumanMessage(query),
            ]
        }
    )

    for message in response["messages"]:
        message.pretty_print()
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    args = parser.parse_args()
    asyncio.run(main(args.query))
