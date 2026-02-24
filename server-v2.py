import argparse
import re
import sys
from typing import Annotated, Any, Literal

import requests
from cachetools import TTLCache
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

mcp = FastMCP(
    name="GDC API MCP Server",
    instructions=(
        "Use the tools of this server to answer questions about genomic variant statistics from data in the GDC. "
        "Currently, we support querying cases by simple somatic mutation, copy number variant, and microsatellite instability. "
        "Queried case sets are cached server-side. Case set intersection is additionally provided server side. "
        "Case counts can be returned for any retrieved or computed case sets."
    ),
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


Project = Annotated[
    str,
    Field(
        description="GDC project name, for example 'TCGA-BRCA'.",
    ),
]
Gene = Annotated[
    str,
    Field(
        description="Gene to query, for example 'BRAF'.",
    ),
]
AAChange = Annotated[
    str,
    Field(
        description="Amino acid change to query (in HGVS protein notation), for example 'V600E'.",
    ),
]
CNVChange = Annotated[
    Literal["gain", "amplification", "heterozygous deletion", "homozygous deletion"],
    Field(
        description="Copy number variation change to query, for example 'homozygous deletion'.",
    ),
]
MSIStatus = Annotated[
    Literal["msi", "mss"],
    Field(
        description="Microsatellite instability status, 'msi' = microsatellite instable, 'MSS' = microsatellite stable",
    ),
]
CaseSetId = Annotated[
    str,
    Field(
        description=(
            "ID representing a set of cases matching a specified query. "
            "The retrieved cases are cached server side and are referenced by this identifier. "
            "The ID additionally encodes the method by which the case set was computed, for example 'SSM-in-BRAF'."
        ),
    ),
]
CaseCount = Annotated[
    int,
    Field(
        description="Number of cases for a retrieved or computed case set.",
    ),
]


@mcp.tool()
def get_simple_somatic_mutation_occurrences(
    gene: Gene,
    aa_change: AAChange | None = None,
) -> CaseSetId:
    """
    A tool to query the GDC API for cases with simple somatic mutations (SSMs).
    This tool searches for SSMs within a given gene, and optionally with a specified amino acid change.
    The resulting case set is cached server side and can be referenced using the unique identifier returned by this tool.
    """
    print(
        f"get_simple_somatic_mutation_occurrences(gene={repr(gene)}, aa_change={repr(aa_change)})",
        file=sys.stderr,
    )

    cache_id = f"Cases-SSM-{gene}"
    if aa_change is not None:
        cache_id = f"{cache_id}-{aa_change}"

    # if we've already done this retrieval, refresh it in the cache and shortcut return
    if cache_id in case_cache:
        case_cache[cache_id] = case_cache[cache_id]
        return cache_id

    # first get SSMs for the given query parameters, either by gene & AA change or just gene
    if aa_change is not None:
        _filters = {
            "op": "in",
            "content": {
                "field": "gene_aa_change",
                "value": [f"{gene} {aa_change}"],  # e.g. 'BRAF V600E'
            },
        }
    else:
        _filters = {
            "op": "in",
            "content": {
                "field": "consequence.transcript.gene.symbol",
                "value": [gene],
            },
        }
    hits = gdc_query_all(
        endpoint="ssms",
        filters=_filters,
        fields=["gene_aa_change", "ssm_id"],
    )
    ssm_ids = [hit["ssm_id"] for hit in hits]

    # then get cases matching those SSMs
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
    case_ids = set([hit["case"]["case_id"] for hit in hits])
    case_cache[cache_id] = list(case_ids)

    return cache_id


@mcp.tool()
def get_copy_number_variant_occurrences(
    gene: Gene,
    cnv_change: CNVChange | None = None,
) -> CaseSetId:
    """
    A tool to query the GDC API for cases with copy number variations (CNVs).
    This tool searches for CNVs within a given gene, and optionally with a specific change type.
    The resulting case set is cached server side and can be referenced using the unique identifier returned by this tool.
    """
    print(
        f"get_copy_number_variant_occurrences(gene={repr(gene)}, cnv_change={repr(cnv_change)})",
        file=sys.stderr,
    )

    cache_id = f"Cases-CNV-{gene}"
    if cnv_change is not None:
        cache_id = f"{cache_id}-{cnv_change}"

    # if we've already done this retrieval, refresh it in the cache and shortcut return
    if cache_id in case_cache:
        case_cache[cache_id] = case_cache[cache_id]
        return cache_id

    # apparently `heterozygous deletion` change type is `loss` so remap it
    # keep the enum for the LLM to help it disambiguate the options
    # see: https://github.com/uc-cdis/gdc-qag/blob/07af83ecae960bd6f62347c473268ff73e725325/check_6k_mutations_withTable2.py#L541-L559
    if cnv_change == "heterozygous deletion":
        cnv_change = "loss"  # type: ignore

    ops = [
        {
            "op": "in",
            "content": {
                "field": "cnv.consequence.gene.symbol",
                "value": [gene],
            },
        },
    ]
    if cnv_change is not None:
        ops.append(
            {
                "op": "in",
                "content": {
                    "field": "cnv.cnv_change_5_category",
                    "value": [cnv_change],
                },
            }
        )

    hits = gdc_query_all(
        endpoint="cnv_occurrences",
        filters={
            "op": "and",
            "content": ops,
        },
        fields=[
            "cnv.cnv_change",
            "cnv.cnv_change_5_category",
            "cnv.consequence.gene.symbol",
            "case.submitter_id",
            "case.case_id",
        ],
    )
    case_ids = set([hit["case"]["case_id"] for hit in hits])
    case_cache[cache_id] = list(case_ids)

    return cache_id


@mcp.tool()
def get_microsatellite_instability_occurrences(
    msi_status: MSIStatus = "msi",
) -> CaseSetId:
    """
    A tool to query the GDC API for cases with microsatellite instability (MSI).
    This tool searches for either MSI or MSS status, by default MSI.
    The resulting case set is cached server side and can be referenced using the unique identifier returned by this tool.
    """
    print(
        f"get_microsatellite_instability_occurrences(msi_status={repr(msi_status)})",
        file=sys.stderr,
    )

    cache_id = f"Cases-MSI-{msi_status}"

    # if we've already done this retrieval, refresh it in the cache and shortcut return
    if cache_id in case_cache:
        case_cache[cache_id] = case_cache[cache_id]
        return cache_id

    # MSI is stored at the file level, so we need to query the files and aggregate back up to the cases
    hits = gdc_query_all(
        endpoint="files",
        filters={
            "op": "and",
            "content": [
                {"op": "in", "content": {"field": "msi_status", "value": [msi_status]}},
                {"op": "in", "content": {"field": "data_format", "value": ["BAM"]}},
            ],
        },
        fields=[
            "msi_status",
            "msi_score",
            "cases.submitter_id",
            "cases.case_id",
        ],
    )

    case_ids = set()
    for hit in hits:
        for case in hit.get("cases", []):
            case_ids.add(case["case_id"])
    case_cache[cache_id] = list(case_ids)

    return cache_id


@mcp.tool()
def get_cases_by_project(project: Project) -> CaseSetId:
    """
    A tool to query the GDC API for cases of a project, for example 'TCGA-BRCA'.
    The resulting case set is cached server side and can be referenced using the unique identifier returned by this tool.
    """
    print(
        f"get_cases_by_project(project={repr(project)})",
        file=sys.stderr,
    )

    cache_id = f"Cases-Project-{project}"

    # if we've already done this retrieval, refresh it in the cache and shortcut return
    if cache_id in case_cache:
        case_cache[cache_id] = case_cache[cache_id]
        return cache_id

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
    case_ids = set([hit["id"] for hit in hits])
    case_cache[cache_id] = list(case_ids)

    return cache_id


@mcp.tool()
def compute_case_intersection(
    case_set_id_A: CaseSetId,
    case_set_id_B: CaseSetId,
) -> CaseSetId:
    """
    A tool to compute the intersection between two case sets.
    The resulting intersected case set is cached server side and can be referenced using the unique identifier returned by this tool.
    """
    print(
        f"compute_case_intersection(case_set_id_A={repr(case_set_id_A)}, case_set_id_B={repr(case_set_id_B)})",
        file=sys.stderr,
    )

    cache_id = f"Cases-Intersect-({case_set_id_A})-AND-({case_set_id_B})"

    # if we've already done this retrieval, refresh it in the cache and shortcut return
    if cache_id in case_cache:
        case_cache[cache_id] = case_cache[cache_id]
        return cache_id

    for case_set_id in [case_set_id_A, case_set_id_B]:
        if case_set_id not in case_cache:
            raise ToolError(
                f"Case set {case_set_id} was not found in the server side cache, perhaps it expired? "
                f"Try requerying for those cases to cache it again. {suggest_tool_from_case_set_id(case_set_id)}"
            )
        # refresh the subsets since we're using them
        case_cache[case_set_id] = case_cache[case_set_id]

    cases_A = set(case_cache[case_set_id_A])
    cases_B = set(case_cache[case_set_id_B])

    A_and_B = cases_A & cases_B
    case_cache[cache_id] = list(A_and_B)

    return cache_id


@mcp.tool()
def get_case_set_size(
    case_set_id: CaseSetId,
) -> CaseCount:
    """
    A tool to retireve the size of a precomputed case set.
    The case set must first be cached server side by one of the other tools provided by this MCP server.
    """
    print(
        f"get_case_set_size(case_set_id={repr(case_set_id)})",
        file=sys.stderr,
    )

    if case_set_id not in case_cache:
        raise ToolError(
            f"Case set {case_set_id} was not found in the server side cache, perhaps it expired? "
            f"Try requerying for those cases to cache it again. {suggest_tool_from_case_set_id(case_set_id)}"
        )

    # refresh the subsets since we're using them
    case_cache[case_set_id] = case_cache[case_set_id]

    return len(case_cache[case_set_id])


TOOL_TO_CACHE_ID_PATTERN = {
    "compute_case_intersection": re.compile(
        r"Cases-Intersect-\((?P<case_set_id_A>.+)\)-AND-\((?P<case_set_id_B>.+)\)",
    ),
    "get_simple_somatic_mutation_occurrences": re.compile(
        r"Cases-SSM-(?P<gene>[^-]+)(?:-(?P<aa_change>.+))?",
    ),
    "get_copy_number_variant_occurrences": re.compile(
        r"Cases-CNV-(?P<gene>[^-]+)(?:-(?P<cnv_change>.+))?",
    ),
    "get_microsatellite_instability_occurrences": re.compile(
        r"Cases-MSI-(?P<msi_status>.+)",
    ),
    "get_cases_by_project": re.compile(
        r"Cases-Project-(?P<project>.+)",
    ),
}


def suggest_tool_from_case_set_id(case_set_id: CaseSetId) -> str:
    for tool_name, pattern in TOOL_TO_CACHE_ID_PATTERN.items():
        if (m := pattern.match(case_set_id)) is not None:
            tool_args = ", ".join([f"{k}={v}" for k, v in m.groupdict().items()])
            return (
                f"Based on the provided case_set_id={case_set_id}, "
                f"it looks like you need to use the following tool with these args: "
                f"{tool_name}({tool_args})"
            )
    return (
        f"The provided case_set_id={case_set_id} did not match any known patterns returned by our tools. "
        f"Are you sure the tools in this MCP server were used to query for cases?"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t", "--transport", required=True, choices=["sse", "stdio", "streamable-http"]
    )
    args = parser.parse_args()
    mcp.run(transport=args.transport)
