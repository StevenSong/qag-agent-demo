import sys
from typing import Any

import requests

from ._defines import GDC_API, CaseSetId

TOOL_CACHE_ID_TEMPLATES = {
    "compute_case_intersection": "Cases-Intersect-({case_set_id_A})-({case_set_id_B})",
    "compute_case_union": "Cases-Union-({case_set_id_A})-({case_set_id_B})",
    "get_simple_somatic_mutation_occurrences": "Cases-SSM-({gene})-({aa_change})",
    "get_copy_number_variant_occurrences": "Cases-CNV-({gene})-({cnv_change})",
    "get_microsatellite_instability_occurrences": "Cases-MSI-({msi_status})",
    "get_cases_by_project": "Cases-Project-({project})",
    "get_cases_by_cohort_description": "Cases-Cohort-({cohort_description})",
}


def suggest_tool_from_case_set_id(case_set_id: CaseSetId) -> str:
    match = match_template_and_params(case_set_id, TOOL_CACHE_ID_TEMPLATES)
    if match is not None:
        tool_name, tool_params = match
        tool_args = ", ".join([f"{k}={v}" for k, v in tool_params.items()])
        return (
            f"Based on the provided case_set_id={case_set_id}, "
            f"it looks like you need to use the following tool with these args: "
            f"{tool_name}({tool_args})"
        )
    return (
        f"The provided case_set_id={case_set_id} did not match any known patterns returned by our tools. "
        f"Are you sure the tools in this MCP server were used to query for cases?"
    )


def match_template_and_params(
    identifier: str, templates: dict[str, str]
) -> tuple[str, dict[str, str]] | None:
    for func_name, template in templates.items():
        prefix = template.split("-(")[0]
        if identifier.startswith(prefix):
            params = extract_top_level_params(identifier)
            names = extract_top_level_params(template)
            if len(params) != len(names):
                raise ValueError(
                    f"Number of parameters ({len(names)}) in matched template ({template}) "
                    f"does not match the number of parameters ({len(params)}) in the identifier ({identifier})"
                )
            return (func_name, {n.strip("{}"): p for n, p in zip(names, params)})
    return None


def extract_top_level_params(identifier: str) -> list[str]:
    params = []
    stack = []
    for i, c in enumerate(identifier):
        if c == "(":
            stack.append(i)
        elif c == ")":
            if len(stack) == 0:
                raise IndexError("No matching closing parens at: " + str(i))
            opening_idx = stack.pop()
            closing_idx = i
            if len(stack) == 0:  # top level paren
                params.append(identifier[opening_idx + 1 : closing_idx])

    if len(stack) > 0:
        raise IndexError("No matching opening parens at: " + str(stack.pop()))

    return params


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
