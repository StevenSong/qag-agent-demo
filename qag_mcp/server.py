import argparse
import json
import sys

from cachetools import TTLCache
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from ._defines import (
    AAChange,
    CaseCount,
    CaseSetId,
    CNVChange,
    CohortDescription,
    Gene,
    MSIStatus,
    Project,
)
from ._utils import gdc_query_all, suggest_tool_from_case_set_id

case_cache = TTLCache(maxsize=1000, ttl=3600)


def get_simple_somatic_mutation_occurrences(
    gene: Gene,
    aa_change: AAChange = None,
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


def get_copy_number_variant_occurrences(
    gene: Gene,
    cnv_change: CNVChange = None,
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


def make_cohort_copilot_tool(generate_filter):
    # The method to generate_filter should be modular so that improvements to cohort copilot
    # can be reflected simply by using a revised implementation of generate_filter

    def get_cases_by_cohort_description(
        cohort_description: CohortDescription,
    ) -> CaseSetId:
        """
        A tool to query the GDC API for cases of a described cohort, for example 'cases from the TCGA-BRCA project' or 'cases of non-smoking patients'.
        The resulting case set is cached server side and can be referenced using the unique identifier returned by this tool.
        While this tool can take natural language inputs, it is best used with very simple, single attribute descriptions.
        Do NOT provide gene filters to this tool.
        """
        print(
            f"get_cases_by_cohort_description(cohort_description={repr(cohort_description)})",
            file=sys.stderr,
        )

        cache_id = f"Cases-Cohort-{cohort_description}"

        # if we've already done this retrieval, refresh it in the cache and shortcut return
        if cache_id in case_cache:
            case_cache[cache_id] = case_cache[cache_id]
            return cache_id

        filter_str = generate_filter(cohort_description)

        # NOTE: there's not a great way in the current tool design to surface the cohort filter to the user, for now just print it
        print(f"Generated Cohort Filter:\n{filter_str}", file=sys.stderr)

        hits = gdc_query_all(
            endpoint="cases",
            filters=json.loads(filter_str),
            fields=["submitter_id"],
        )
        case_ids = set([hit["id"] for hit in hits])
        case_cache[cache_id] = list(case_ids)

        return cache_id

    return get_cases_by_cohort_description


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


def compute_case_union(
    case_set_id_A: CaseSetId,
    case_set_id_B: CaseSetId,
) -> CaseSetId:
    """
    A tool to compute the union between two case sets.
    The resulting unioned case set is cached server side and can be referenced using the unique identifier returned by this tool.
    """
    print(
        f"compute_case_union(case_set_id_A={repr(case_set_id_A)}, case_set_id_B={repr(case_set_id_B)})",
        file=sys.stderr,
    )

    cache_id = f"Cases-Union-({case_set_id_A})-AND-({case_set_id_B})"

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

    A_and_B = cases_A | cases_B
    case_cache[cache_id] = list(A_and_B)

    return cache_id


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--transport",
        required=True,
        choices=["sse", "stdio", "streamable-http"],
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
    )
    parser.add_argument(
        "--use-cohort-copilot",
        default=False,
        action="store_true",
    )
    args = parser.parse_args()

    mcp = FastMCP(
        name="GDC API MCP Server",
        instructions=(
            "Use the tools of the GDC MCP server to answer questions about genomic variant statistics from data in the GDC. "
            "Currently, we support querying cases by simple somatic mutation, copy number variant, and microsatellite instability. "
            "Do not assume that 'mutation' simply means somatic mutation, even if given a specific gene (it's also valid to query for CNV mutations in a gene). "
            "Since somatic mutations and copy number variation can both be considered mutations but this may be ambiguous, "
            "so if a user asks for 'mutations' without further specification, you should always stop and clarify with the user. "
            "You should never make the assumption about what the user means. "
            "Queried case sets are cached server-side. Case set intersection and union is additionally provided server side. "
            "Case counts can be returned for any retrieved or computed case sets."
        ),
        port=args.port,
    )

    mcp.add_tool(get_simple_somatic_mutation_occurrences)
    mcp.add_tool(get_copy_number_variant_occurrences)
    mcp.add_tool(get_microsatellite_instability_occurrences)
    if args.use_cohort_copilot:
        # NOTE: with cohort copilot v1, importing will load a model onto GPU so defer until needed
        from .cohort_copilot import generate_filter

        get_cases_by_cohort_description = make_cohort_copilot_tool(generate_filter)
        mcp.add_tool(get_cases_by_cohort_description)
    else:
        mcp.add_tool(get_cases_by_project)
    mcp.add_tool(compute_case_intersection)
    mcp.add_tool(compute_case_union)
    mcp.add_tool(get_case_set_size)

    mcp.run(transport=args.transport)
