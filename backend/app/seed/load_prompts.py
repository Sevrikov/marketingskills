from sqlalchemy.orm import Session

from app.seed.prompt_templates import SEED_PROMPTS
from app.services.prompt_templates import DuplicatePromptTemplate, create_prompt_template


def load_seed_prompts(db: Session) -> int:
    created = 0
    for prompt in SEED_PROMPTS:
        try:
            create_prompt_template(db, prompt)
        except DuplicatePromptTemplate:
            continue
        created += 1
    return created
