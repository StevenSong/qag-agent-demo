import argparse
import sys
import uuid
from typing import Annotated, Any, Literal

import requests
from cachetools import TTLCache
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    name="GDC API MCP Server",
    instructions="Use the tools of this server to query data from the GDC.",
)

case_cache = TTLCache(maxsize=1000, ttl=3600)
GDC_API = "https://api.gdc.cancer.gov"


def gdc_query_all(
    endpoint: str,
    filters: dict,
    fields: list[str] | None = None,
    page_size: int = 1000,
) -> list[dict[str, Any]]:
    url = f"{GDC_API}/{endpoint}"
    all_hits = []
    offset = 0

    while True:
        payload = {
            "filters": filters,
            "from": offset,
            "size": page_size,
        }

        if fields:
            # even if using post, fields needs to be a comma-separated string
            payload["fields"] = ",".join(fields)

        response = requests.post(url, json=payload)
        response.raise_for_status()
        resp_json = response.json()

        if resp_json["warnings"]:
            print(resp_json["warnings"], file=sys.stderr)

        data = resp_json["data"]

        hits = data["hits"]
        all_hits.extend(hits)

        pagination = data["pagination"]
        total = pagination["total"]

        # print(f"Retrieved {len(all_hits)} / {total}", file=sys.stderr)

        offset += page_size
        if offset >= total:
            break

    return all_hits


# fmt: off
Project = Annotated[str, Field(description="GDC project name, for example 'TCGA-BRCA'")]
Gene = Annotated[str, Field(description="Gene to query, for example 'BRAF'")]
AaChange = Annotated[str, Field(description="Amino acid change to query (in HGVS protein notation), for example 'V600E'")]
CnvChange = Annotated[Literal["loss", "gain", "amplification", "homozygous deletion"], Field(description="Copy number variation change to query, for example 'homozygous deletion'")]
SsmIds = Annotated[list[str], Field(description="List of SSM IDs (UUIDs) matching the search parameters")]
CaseIds = Annotated[str, Field(description="UUID representing a set of case IDs matching a specified query. The retrieved cases are cached server side and are referenced by this unique identifier (UUID)")]
# fmt: on


class CooccurrenceByProjectResult(BaseModel):
    cooccurrence_count: int = Field(
        description="Number of overlapping between two sets of cases within a project."
    )
    total_project_cases: int = Field(
        description="Total number of cases within a project."
    )
    cooccurrence_frequency: float = Field(
        description="Fraction of all project cases where two sets of cases overlap."
    )


@mcp.tool()
def get_simple_somatic_mutation_ids(gene: Gene, aa_change: AaChange) -> SsmIds:
    """
    A tool to query the GDC API for SSMs matching a specified amino acid change within a gene, for example 'BRAF V600E'. Note that a single amino acid change may be the result of multiple somatic mutations, so this tool will return all matched SSMs for the given amino acid change.
    """
    print(
        f"get_simple_somatic_mutation_ids(gene={repr(gene)}, aa_change={repr(aa_change)})",
        file=sys.stderr,
    )
    hits = gdc_query_all(
        endpoint="ssms",
        filters={
            "op": "in",
            "content": {
                "field": "gene_aa_change",
                "value": [
                    f"{gene} {aa_change}",  # e.g. 'BRAF V600E'
                ],
            },
        },
        fields=["gene_aa_change", "ssm_id"],
    )
    return [hit["ssm_id"] for hit in hits]


@mcp.tool()
def get_simple_somatic_mutation_occurrences(ssm_ids: SsmIds) -> CaseIds:
    """
    A tool to query the GDC API for cases with the specified SSMs. If multiple SSMs are given, this tool computes the union of cases for those SSMs. This is useful in case multiple SSMs result in a specific amino acid change. This tool should not be used to compute intersections or cooccurrences! The resulting case IDs are cached server side and can be referenced using a unique identifier returned by this tool.
    """
    print(
        f"get_simple_somatic_mutation_occurrences({repr(ssm_ids)})",
        file=sys.stderr,
    )
    hits = gdc_query_all(
        endpoint="ssm_occurrences",
        filters={
            "op": "in",
            "content": {
                "field": "ssm.ssm_id",
                "value": ssm_ids,
            },
        },
        fields=["ssm.ssm_id", "case.submitter_id", "case.case_id"],
    )

    cache_id = str(uuid.uuid4())
    case_cache[cache_id] = [hit["case"]["case_id"] for hit in hits]
    return cache_id


@mcp.tool()
def get_copy_number_variant_occurrences(gene: Gene, cnv_change: CnvChange) -> CaseIds:
    """
    A tool to query the GDC API for cases with a copy number change within a specific gene. The resulting case IDs are cached server side and can be referenced using a unique identifier returned by this tool.
    """
    print(
        f"get_copy_number_variant_occurrences(gene={repr(gene)}, cnv_change={repr(cnv_change)})",
        file=sys.stderr,
    )
    hits = gdc_query_all(
        endpoint="cnv_occurrences",
        filters={
            "op": "and",
            "content": [
                {
                    "op": "in",
                    "content": {
                        "field": "cnv.cnv_change_5_category",
                        "value": [cnv_change],
                    },
                },
                {
                    "op": "in",
                    "content": {
                        "field": "cnv.consequence.gene.symbol",
                        "value": [gene],
                    },
                },
            ],
        },
        fields=[
            "cnv.cnv_change",
            "cnv.cnv_change_5_category",
            "cnv.consequence.gene.symbol",
            "case.submitter_id",
            "case.case_id",
        ],
    )

    cache_id = str(uuid.uuid4())
    case_cache[cache_id] = [hit["case"]["case_id"] for hit in hits]
    return cache_id


@mcp.tool()
def get_cases_by_project(project: Project) -> CaseIds:
    """
    A tool to query the GDC API for cases within a specified project, for example 'TCGA-BRCA'. The resulting case IDs are cached server side and can be referenced using a unique identifier returned by this tool.
    """
    print(
        f"get_cases_by_project({repr(project)})",
        file=sys.stderr,
    )
    hits = gdc_query_all(
        endpoint="cases",
        filters={
            "op": "in",
            "content": {
                "field": "cases.project.project_id",
                "value": [project],
            },
        },
        fields=["project.project_id", "submitter_id"],
    )

    cache_id = str(uuid.uuid4())
    case_cache[cache_id] = [hit["id"] for hit in hits]
    return cache_id


@mcp.tool()
def get_case_cooccurrence_frequency_by_project(
    cases_A: CaseIds,
    cases_B: CaseIds,
    cases_project: CaseIds,
) -> CooccurrenceByProjectResult:
    """
    A tool to compute the cooccurrence frequency between two conditions within a
    project. The conditions and project should be specified as case sets. Specifically,
    this tool computes |(cases_A & cases_B) & cases_project| / |cases_project|.
    The specified case sets should be first precomputed using other tools and cached server side.
    The arguments to this tool are then the unique identifiers to retrieve those case IDs.
    """
    print(
        f"get_case_cooccurrence_frequency_by_project(\n"
        f"    cases_A={repr(cases_A)},\n"
        f"    cases_B={repr(cases_B)},\n"
        f"    cases_project={repr(cases_project)},\n"
        f")",
        file=sys.stderr,
    )
    _cases_A = set(case_cache[cases_A])
    _cases_B = set(case_cache[cases_B])
    _cases_project = set(case_cache[cases_project])

    A_and_B = _cases_A & _cases_B
    project_A_and_B = A_and_B & _cases_project

    return CooccurrenceByProjectResult(
        cooccurrence_count=len(project_A_and_B),
        total_project_cases=len(_cases_project),
        cooccurrence_frequency=len(project_A_and_B) / len(_cases_project),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--transport", default="sse", choices=["sse", "stdio"])
    args = parser.parse_args()
    mcp.run(transport=args.transport)
