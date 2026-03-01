from typing import Annotated, Literal

from pydantic import Field

GDC_API = "https://api.gdc.cancer.gov"

Project = Annotated[
    str,
    Field(
        description="GDC project name, for example 'TCGA-BRCA'.",
    ),
]
CohortDescription = Annotated[
    str,
    Field(
        description="Natural language description of a cohort of cases, for example 'cases from male patients with lung cancer'.",
    ),
]
Gene = Annotated[
    str,
    Field(
        description="Gene to query, for example 'BRAF'.",
    ),
]
AAChange = Annotated[
    str | None,
    Field(
        description="(Optional) Amino acid change to query (in HGVS protein notation), for example 'V600E'.",
    ),
]
CNVChange = Annotated[
    Literal["gain", "amplification", "heterozygous deletion", "homozygous deletion"]
    | None,
    Field(
        description="(Optional) Copy number variation change to query. Valid options are 'gain', 'amplification', 'heterozygous deletion', or 'homozygous deletion'.",
    ),
]
MSIStatus = Annotated[
    Literal["msi", "mss"],
    Field(
        description="Microsatellite instability status. Valid options are 'msi' for microsatellite instable or 'mss' for microsatellite stable.",
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

TOOL_CACHE_ID_TEMPLATES = {
    "compute_case_intersection": "Cases-Intersect-({case_set_id_A})-({case_set_id_B})",
    "compute_case_union": "Cases-Union-({case_set_id_A})-({case_set_id_B})",
    "get_simple_somatic_mutation_occurrences": "Cases-SSM-({gene})-({aa_change})",
    "get_copy_number_variant_occurrences": "Cases-CNV-({gene})-({cnv_change})",
    "get_microsatellite_instability_occurrences": "Cases-MSI-({msi_status})",
    "get_cases_by_project": "Cases-Project-({project})",
    "get_cases_by_cohort_description": "Cases-Cohort-({cohort_description})",
}
