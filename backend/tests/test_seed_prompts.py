from app.seed.load_prompts import load_seed_prompts
from app.services.prompt_templates import list_prompt_templates


def test_load_seed_prompts_is_idempotent(db_session):
    first_count = load_seed_prompts(db_session)
    second_count = load_seed_prompts(db_session)
    prompts = list_prompt_templates(db_session, limit=100)

    assert first_count > 0
    assert second_count == 0
    assert len(prompts) == first_count
