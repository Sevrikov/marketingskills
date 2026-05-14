from app.models.prompt_template import PromptTemplateStatus
from app.schemas.prompt_template import PromptTemplateCreate


SEED_PROMPTS: list[PromptTemplateCreate] = [
    PromptTemplateCreate(
        key="ecommerce.product_normalization.v1",
        name="Ecommerce Product Normalization",
        version="1.0.0",
        task_type="product_normalization",
        provider="gemini",
        model="gemini-2.5-flash-lite",
        status=PromptTemplateStatus.ACTIVE,
        system_prompt=(
            "You normalize raw e-commerce product input into structured fields. "
            "Preserve uncertainty and never invent identifiers."
        ),
        user_template=(
            "Normalize this product input into JSON.\n\n"
            "Raw product:\n{raw_product}\n\n"
            "Required fields: title, brand, model, category, sku, gtin, mpn, price, "
            "currency, availability, source_url, missing_fields, research_needed."
        ),
        expected_output="Strict JSON object with normalized product fields.",
        validation_schema={"type": "object"},
    ),
    PromptTemplateCreate(
        key="ecommerce.customer_pain_research.v1",
        name="Customer Pain Research",
        version="1.0.0",
        task_type="customer_pain_research",
        provider="gemini",
        model="gemini-2.5-flash-lite",
        status=PromptTemplateStatus.ACTIVE,
        system_prompt=(
            "You research the real customer pain, buyer problem, trigger events, "
            "objections and proof map for ecommerce products. Separate confirmed "
            "facts from hypotheses and never invent reviews, savings or outcomes."
        ),
        user_template=(
            "Research the buyer pain solved by this product/topic.\n\n"
            "Subject: {subject}\n"
            "Product: {product}\n"
            "Specifications: {specifications}\n"
            "Research report: {research_report}\n\n"
            "Return a pain_profile JSON with primary_pain, secondary_pains, "
            "buyer_words, use_contexts, trigger_events, proof_map, objections, "
            "content_guidance for product description, article, infographic, video, "
            "Shorts and Viber, do_not_claim, sources and missing_or_risky_data."
        ),
        expected_output="Strict pain_profile JSON with evidence and source ids.",
        validation_schema={"type": "object"},
    ),
    PromptTemplateCreate(
        key="ecommerce.aeo_product_description.v1",
        name="AEO Product Description",
        version="1.0.0",
        task_type="product_card",
        provider="gemini",
        model="gemini-2.5-flash-lite",
        status=PromptTemplateStatus.ACTIVE,
        system_prompt=(
            "You write expert e-commerce product descriptions optimized for SEO and "
            "answer-engine visibility. Every important paragraph must be a "
            "self-contained answer block."
        ),
        user_template=(
            "Create an AEO product card from the data below.\n\n"
            "Product: {product}\n"
            "Specifications: {specifications}\n"
            "Research report: {research_report}\n\n"
            "Approved pain_profile: {pain_profile}\n\n"
            "First identify the confirmed customer pain from the research report. "
            "If it is confirmed, make it visible in the short answer, use cases, "
            "benefits, limitations and FAQ. Connect each benefit to the pain and "
            "to product facts. If the pain is not confirmed, mark it as a hypothesis "
            "or omit it.\n\n"
            "Include H1, short answer, buyer pain/problem solved, use cases, benefits, "
            "limitations, specs, FAQ, meta title, meta description and alt texts."
        ),
        expected_output="Markdown product card plus metadata fields.",
        validation_schema={"type": "object"},
    ),
    PromptTemplateCreate(
        key="ecommerce.content_critic.v1",
        name="Content Critic",
        version="1.0.0",
        task_type="critic",
        provider="gemini",
        model="gemini-2.5-flash-lite",
        status=PromptTemplateStatus.ACTIVE,
        system_prompt=(
            "You are a strict editor checking factual accuracy, AEO structure, "
            "commercial usefulness, and unsupported claims."
        ),
        user_template=(
            "Critique this draft.\n\nDraft:\n{draft}\n\n"
            "Check: facts, sources, answer blocks, missing sections, vague claims, "
            "SEO/AEO structure, buyer usefulness, customer pain integration, "
            "pain-to-proof mapping and unsupported pain overclaims."
        ),
        expected_output="Structured critique with prioritized issues and rewrite instructions.",
        validation_schema={"type": "object"},
    ),
    PromptTemplateCreate(
        key="ecommerce.rewriter.v1",
        name="Content Rewriter",
        version="1.0.0",
        task_type="rewrite",
        provider="gemini",
        model="gemini-2.5-flash-lite",
        status=PromptTemplateStatus.ACTIVE,
        system_prompt="You rewrite content according to critique while preserving verified facts.",
        user_template=(
            "Rewrite the draft using the critique.\n\n"
            "Draft:\n{draft}\n\nCritique:\n{critique}\n\n"
            "Return the improved final version."
        ),
        expected_output="Improved markdown content.",
        validation_schema={"type": "object"},
    ),
    PromptTemplateCreate(
        key="ecommerce.video_brief.v1",
        name="Marketing Video Brief",
        version="1.0.0",
        task_type="video_brief",
        provider="gemini",
        model="gemini-2.5-flash-lite",
        status=PromptTemplateStatus.ACTIVE,
        system_prompt=(
            "You create marketing video briefs for long videos and shorts. "
            "Do not generate video prompts before the brief is approved."
        ),
        user_template=(
            "Create a video brief.\n\nProduct/topic: {subject}\n"
            "Goal: {goal}\nAudience: {audience}\nPlatform: {platform}\n\n"
            "Start from the confirmed buyer pain in the research report when available. "
            "The hook and first scene should show the pain or buying question, then "
            "connect product facts to proof. If the pain is not confirmed, avoid "
            "fear-based claims.\n\n"
            "Include key message, pain angle, offer, CTA, required facts, forbidden "
            "claims, tone, duration, subtitles and scene list."
        ),
        expected_output="Markdown video brief and structured scene outline.",
        validation_schema={"type": "object"},
    ),
]
