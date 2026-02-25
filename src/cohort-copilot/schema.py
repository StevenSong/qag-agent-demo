import os
from enum import Enum
from typing import Annotated, Literal, get_args, get_type_hints

import yaml
from pydantic import BaseModel, Field, StringConstraints


class InnerOp(Enum):
    IN = "in"


class InnerRangeOp(Enum):
    EQ = "="
    LT = "<"
    GT = ">"
    LE = "<="
    GE = ">="


class MiddleOp(Enum):
    AND = "and"


class OuterOp(Enum):
    AND = "and"


class InnerAgeDxContent(BaseModel):
    field: Literal["cases.diagnoses.age_at_diagnosis"]
    value: Annotated[int, Field(ge=0, le=32872)]


class InnerYearDxContent(BaseModel):
    field: Literal["cases.diagnoses.year_of_diagnosis"]
    value: Annotated[int, Field(ge=1900, le=2050)]


class InnerCigDayContent(BaseModel):
    field: Literal["cases.exposures.cigarettes_per_day"]
    value: Annotated[int, Field(ge=0, le=999999)]


class InnerPackYrContent(BaseModel):
    field: Literal["cases.exposures.pack_years_smoked"]
    value: Annotated[int, Field(ge=0, le=999999)]


class InnerCigStrtContent(BaseModel):
    field: Literal["cases.exposures.tobacco_smoking_onset_year"]
    value: Annotated[int, Field(ge=1900, le=2050)]


excluded_values = set()
for alt_inner in [
    InnerYearDxContent,
    InnerCigDayContent,
    InnerPackYrContent,
    InnerCigStrtContent,
]:
    field_type = get_type_hints(alt_inner)["field"]
    excluded_values |= set(get_args(field_type))

rel_path = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(rel_path, "r") as f:
    CONFIG = yaml.safe_load(f)
all_other_fields = tuple(
    [
        card["field"]
        for tab in CONFIG["tabs"]
        for card in tab["cards"]
        if card["field"] not in excluded_values
    ]
)


class InnerStrContent(BaseModel):
    field: Literal[all_other_fields]  # type: ignore - runtime literal
    value: list[Annotated[str, StringConstraints(min_length=1, max_length=128)]]


class Inner(BaseModel):
    op: InnerOp
    content: InnerStrContent


class InnerRange(BaseModel):
    op: InnerRangeOp
    content: (
        InnerAgeDxContent
        | InnerYearDxContent
        | InnerCigDayContent
        | InnerPackYrContent
        | InnerCigStrtContent
    )


class Middle(BaseModel):
    op: MiddleOp
    content: list[Inner | InnerRange]


class GDCCohortSchema(BaseModel):
    op: OuterOp
    content: list[Middle | Inner | InnerRange]
