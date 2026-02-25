from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.toolsets.fastmcp import FastMCPToolset

toolset = FastMCPToolset("http://localhost:8000/mcp")

ollama_model = OpenAIChatModel(
    model_name="gpt-oss:120b",
    provider=OllamaProvider(base_url="http://localhost:11434/v1"),
)


def make_agent(output_type: BaseModel | None = None) -> Agent:
    if output_type is None:
        output_type = str
    return Agent(
        ollama_model,
        toolsets=[toolset],
        instructions="You are a helpful bioinformatics assistant with access to specialized tools to query information about genetic mutations using the Genomic Data Commons (GDC). Use the tools to answer questions. Multiple chained tool calls may be required to answer a question.",
        output_type=output_type,
    )


if __name__ == "__main__":
    # either doing bulk evaluation or one off query
    import argparse
    from typing import Annotated

    import pandas as pd
    from pydantic import BaseModel, Field
    from tqdm import tqdm

    class PercentResult(BaseModel):
        percentage: Annotated[
            float, Field(description="Result of GDC variant statistic question")
        ]

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q",
        "--query",
        default="How many TCGA-BRCA cases have a somatic mutation in BRAF?",
        required=False,
    )
    args = parser.parse_args()
    output_type = None
    if args.query.endswith(".csv"):
        # doing bulk eval
        df = pd.read_csv(args.query)
        queries = [
            q + " Make sure to only return a percentage." for q in df["questions"]
        ]
        output_type = PercentResult
    else:
        queries = [args.query]

    # run queries
    agent = make_agent(output_type)
    results = []
    for query in tqdm(queries):
        result = agent.run_sync(query)
        results.append(result)

    if len(results) > 1:
        # save bulk eval
        answers = [r.output.percentage for r in results]
        pd.Series(answers, name="answers").to_csv(
            args.query.replace(".csv", "-answers.csv"),
            index=False,
        )
    else:
        for message in results[0].all_messages():
            print("====================================================")
            print(message)
            print()
    exit(0)

# if we made it here, we're serving the agent with a UI
app = make_agent().to_web()
