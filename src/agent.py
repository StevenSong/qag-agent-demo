import argparse

import uvicorn
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.toolsets.fastmcp import FastMCPToolset


def make_agent(
    mcp_url: str,
    llm_url: str,
    output_type: BaseModel | None = None,
) -> Agent:
    toolset = FastMCPToolset(mcp_url)
    model = OpenAIChatModel(
        model_name="openai/gpt-oss-120b",
        provider=OpenAIProvider(base_url=llm_url, api_key="NONE"),
    )
    if output_type is None:
        output_type = str
    agent = Agent(
        model,
        toolsets=[toolset],
        instructions=(
            "You are a helpful bioinformatics assistant with access to specialized "
            "tools to query information about genetic mutations using the Genomic Data Commons (GDC). "
            "Use the tools to answer questions. Multiple chained tool calls may be required to answer a question. "
            "Also math is hard for LLMs to do in natural language. If you need to do arithmetic, just use the tools."
        ),
        output_type=output_type,
    )

    @agent.tool_plain
    def add(a: float, b: float) -> float:
        """
        compute a + b
        """
        return a + b

    @agent.tool_plain
    def subtract(a: float, b: float) -> float:
        """
        compute a - b
        """
        return a - b

    @agent.tool_plain
    def multiply(a: float, b: float) -> float:
        """
        compute a * b
        """
        return a * b

    @agent.tool_plain
    def divide(a: float, b: float) -> float:
        """
        compute a / b
        """
        return a / b

    return agent


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--query")
    parser.add_argument("-p", "--port", type=int)
    parser.add_argument("--mcp-url", required=True)
    parser.add_argument("--llm-url", required=True)
    args = parser.parse_args()

    # p: None, q: None - run as server w/ default port
    # p: specified, q: None - run as server w/ given port
    # p: None, q: str or csv - run query or queries
    # p: specified, q: str - error
    if args.port is not None and args.query is not None:
        raise ValueError(
            f"Cannot use both --query ({args.query}) and --port ({args.port}), setting port implies serving the agent UI while setting query implies running the agent over provided inputs"
        )

    agent = make_agent(mcp_url=args.mcp_url, llm_url=args.llm_url)

    if args.query is None:
        # server the agent with a UI
        app = agent.to_web()
        port = 8000  # default
        if args.port is not None:
            port = args.port
        uvicorn.run(app, port=port)
    elif args.query.endswith(".csv"):
        # bulk inference
        pass
    else:
        # run single query
        result = agent.run_sync(args.query)
        for message in result.all_messages():
            print("====================================================")
            print(message)
            print()
