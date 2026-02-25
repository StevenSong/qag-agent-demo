import json
import os

from guidance import json as gen_json
from guidance.models import Transformers
from transformers import AutoTokenizer, GPT2LMHeadModel, set_seed

from schema import GDCCohortSchema  # isort: skip

MODEL_NAME = "uc-ctds/gdc-cohort-llm-gpt2-s1M"
TOKENIZER_NAME = MODEL_NAME
MODEL_READ_TOKEN = os.environ.get("MODEL_READ_TOKEN", None)


tok = AutoTokenizer.from_pretrained(TOKENIZER_NAME, token=MODEL_READ_TOKEN)
model = GPT2LMHeadModel.from_pretrained(MODEL_NAME, token=MODEL_READ_TOKEN)
model = model.to("cpu")
model = model.eval()


# Generate cohort filter JSON from free text
def generate_filter(query: str) -> str:
    """
    Converts a free text description of a cancer cohort into a GDC structured cohort filter.

    Args:
        query (str): The free text cohort description

    Returns:
        str: JSON structured GDC cohort filter
    """

    set_seed(42)
    lm = Transformers(
        model=model,
        tokenizer=tok,
    )
    lm += query
    lm += gen_json(
        name="cohort", schema=GDCCohortSchema, temperature=0, max_tokens=1024
    )
    cohort_filter = lm["cohort"]
    cohort_filter = json.dumps(json.loads(cohort_filter), indent=4)

    return cohort_filter
