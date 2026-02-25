from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.toolsets.fastmcp import FastMCPToolset

toolset = FastMCPToolset("http://localhost:8000/mcp")

ollama_model = OpenAIChatModel(
    model_name="gpt-oss:120b",
    provider=OllamaProvider(base_url="http://localhost:11434/v1"),
)

agent = Agent(
    ollama_model,
    toolsets=[toolset],
    instructions="You are a helpful bioinformatics assistant with access to specialized tools to query information about genetic mutations using the Genomic Data Commons (GDC). Use the tools to answer questions. Multiple chained tool calls may be required to answer a question.",
)

app = agent.to_web()

if __name__ == "__main__":
    result = agent.run_sync("How many TCGA-BRCA cases have a somatic mutation in BRAF?")
    print(result.all_messages())
