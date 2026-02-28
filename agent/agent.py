import argparse
import os
from contextlib import asynccontextmanager

import uvicorn
from pydantic_ai import Agent, ConcurrencyLimit
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.messages import (
    PartDeltaEvent,
    PartStartEvent,
    ThinkingPart,
    ThinkingPartDelta,
)
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider


def patch_model_reasoning(model: OpenAIResponsesModel):
    """
    patch a model's response stream to handle reasoning content
    model is patched in-place

    alternate inference providers (like vLLM) support returning raw thinking tokens
    this GH issue requested supporting the reasoning response format: https://github.com/pydantic/pydantic-ai/issues/3191
    the final discussion and implementation ended up moving the tokens to "raw_content":
    https://github.com/pydantic/pydantic-ai/pull/3559
    also see this documentation: https://github.com/pydantic/pydantic-ai/blob/94dc8f888bf5ff20478c43d737e76d5756cb3f1d/docs/thinking.md?plain=1#L41-L42
    this patch surfaces that content as the reasoning summary
    it was easier to collect the reasoning stream than forward them streamed
    """
    _original_request_stream = model.request_stream

    @asynccontextmanager
    async def _patched_request_stream(*args, **kwargs):
        async with _original_request_stream(*args, **kwargs) as stream:
            original_iterator = stream._get_event_iterator

            async def _fixed_iterator():
                thinking_part_indices: set[int] = set()

                async for event in original_iterator():
                    if isinstance(event, PartStartEvent) and isinstance(
                        event.part, ThinkingPart
                    ):
                        thinking_part_indices.add(event.index)
                        yield event

                    elif isinstance(event, PartDeltaEvent) and isinstance(
                        event.delta, ThinkingPartDelta
                    ):
                        pass

                    else:
                        for index in thinking_part_indices:
                            part = stream._parts_manager._parts[index]
                            if isinstance(part, ThinkingPart):
                                if part.provider_details is None:
                                    print(
                                        f"ThinkingPart.provider_details is None: {part}"
                                    )
                                    continue
                                raw = part.provider_details.get("raw_content", "")
                                full_content = (
                                    "".join(raw) if isinstance(raw, list) else raw
                                )
                                if full_content:
                                    yield PartDeltaEvent(
                                        index=index,
                                        delta=ThinkingPartDelta(
                                            content_delta=full_content
                                        ),
                                    )
                        thinking_part_indices.clear()
                        yield event

            stream._get_event_iterator = _fixed_iterator
            yield stream

    model.request_stream = _patched_request_stream


def make_agent(
    mcp_url: str,
    llm_url: str,
    retries: int = 1,
    max_running: int = 4,
    max_queued: int = 8,
) -> Agent:
    mcp_server = MCPServerStreamableHTTP(mcp_url)
    model = OpenAIResponsesModel(
        model_name="openai/gpt-oss-120b",
        provider=OpenAIProvider(base_url=llm_url, api_key="NONE"),
    )
    patch_model_reasoning(model)
    agent = Agent(
        model,
        toolsets=[mcp_server],
        instructions=(
            "You are a helpful bioinformatics assistant with access to specialized "
            "tools to query information about genetic mutations using the Genomic Data Commons (GDC). "
            "Use the tools to answer questions. Multiple chained tool calls may be required to answer a question. "
            "If a user query is ambiguous, stop and ask them to clarify before trying to find the answer. "
            "Also math is hard for LLMs to do in natural language. If you need to do arithmetic, just use the tools."
        ),
        max_concurrency=ConcurrencyLimit(
            max_running=max_running, max_queued=max_queued
        ),
        retries=retries,
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

    @agent.instructions
    async def mcp_server_instructions():
        return mcp_server.instructions

    return agent


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--query")
    parser.add_argument("-p", "--port", type=int)
    parser.add_argument("--mcp-url", required=True)
    parser.add_argument("--llm-url", required=True)
    args = parser.parse_args()

    # p: None, q: None - run as server w/ default port
    # p: int,  q: None - run as server w/ given port
    # p: None, q: str - run query
    # p: int,  q: str - error
    if args.port is not None and args.query is not None:
        raise ValueError(
            f"Cannot use both --query ({args.query}) and --port ({args.port}), setting port implies serving the agent UI while setting query implies running the agent over provided input"
        )

    agent = make_agent(mcp_url=args.mcp_url, llm_url=args.llm_url)

    if args.query is None:
        # serve the agent with a UI - this is just a dev UI! cannot be mounted under a root_path
        # see: https://github.com/pydantic/pydantic-ai/issues/4156
        # rel_dir = os.path.dirname(__file__)
        # app = agent.to_web()

        # start a server for the agent, exposing an AG-UI interface
        # requires a separate app server (CopilotKit) that talks to the agent via AG-UI
        app = agent.to_ag_ui()
        port = 8000  # default
        if args.port is not None:
            port = args.port
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        # run single query
        result = agent.run_sync(args.query)
        for message in result.all_messages():
            print("====================================================")
            print(message)
            print()
