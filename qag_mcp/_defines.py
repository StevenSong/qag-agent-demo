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
