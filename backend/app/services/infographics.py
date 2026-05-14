import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content_research_report import ContentResearchReport
from app.models.content_task import ContentTask
from app.models.infographic_data_pack import InfographicDataPack
from app.models.infographic_design_brief import InfographicDesignBrief
from app.models.infographic_project import InfographicProject, InfographicProjectStatus
from app.models.product import Product
from app.schemas.infographic import InfographicProjectCreate
from app.services.pain_profiles import get_approved_pain_profile_for_product


class MissingInfographicDataPack(ValueError):
    pass


def create_infographic_project(db: Session, payload: InfographicProjectCreate) -> InfographicProject:
    project = InfographicProject(
        scope_type=payload.scope_type,
        scope_id=payload.scope_id or payload.product_id,
        product_id=payload.product_id,
        source_task_id=payload.source_task_id,
        source_research_report_id=payload.source_research_report_id,
        title=payload.title,
        infographic_type=payload.infographic_type,
        target_channel=payload.target_channel,
        created_by=payload.created_by,
        brand_style_json=payload.brand_style_json or _default_brand_style(),
        metadata_json={
            "workflow": "infographic_data_pack_mvp",
            "requires_human_review": True,
        },
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def list_infographic_projects(
    db: Session,
    *,
    product_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[InfographicProject]:
    stmt = select(InfographicProject).order_by(
        InfographicProject.created_at.desc(),
        InfographicProject.id.desc(),
    )
    if product_id:
        stmt = stmt.where(InfographicProject.product_id == product_id)
    if status:
        stmt = stmt.where(InfographicProject.status == status)
    return list(db.scalars(stmt.limit(limit)))


def get_infographic_project(db: Session, project_id: str) -> InfographicProject | None:
    return db.get(InfographicProject, project_id)


def list_infographic_data_packs(db: Session, project_id: str) -> list[InfographicDataPack]:
    stmt = (
        select(InfographicDataPack)
        .where(InfographicDataPack.project_id == project_id)
        .order_by(InfographicDataPack.created_at.asc(), InfographicDataPack.id.asc())
    )
    return list(db.scalars(stmt))


def list_infographic_design_briefs(db: Session, project_id: str) -> list[InfographicDesignBrief]:
    stmt = (
        select(InfographicDesignBrief)
        .where(InfographicDesignBrief.project_id == project_id)
        .order_by(InfographicDesignBrief.created_at.asc(), InfographicDesignBrief.id.asc())
    )
    return list(db.scalars(stmt))


def generate_infographic_data_pack(
    db: Session,
    project: InfographicProject,
) -> InfographicDataPack:
    product = db.get(Product, project.product_id) if project.product_id else None
    source_task = db.get(ContentTask, project.source_task_id) if project.source_task_id else None
    research = _resolve_research(db, project, source_task)
    pain_profile = (
        get_approved_pain_profile_for_product(db, product.id) if product is not None else None
    )
    data_pack = _build_data_pack(project, product, source_task, research, pain_profile)
    missing = data_pack["missing_or_risky_data"]
    source_count = len(data_pack["sources"])
    confidence_score = _confidence_score(data_pack)
    stored = InfographicDataPack(
        project_id=project.id,
        data_pack_json=data_pack,
        source_count=source_count,
        missing_fields_json=missing,
        confidence_score=confidence_score,
    )
    project.status = InfographicProjectStatus.DATA_READY.value
    db.add(stored)
    db.add(project)
    db.commit()
    db.refresh(stored)
    return stored


def generate_infographic_design_brief(
    db: Session,
    project: InfographicProject,
) -> InfographicDesignBrief:
    data_pack = _latest_data_pack(db, project.id)
    if data_pack is None:
        raise MissingInfographicDataPack("Generate infographic data pack before design brief.")
    brief_json = _build_design_brief_json(project, data_pack.data_pack_json)
    prompt_pack = _build_prompt_pack(project, data_pack.data_pack_json, brief_json)
    brief = InfographicDesignBrief(
        project_id=project.id,
        data_pack_id=data_pack.id,
        status="design_prompt_ready",
        brief_markdown=_design_brief_markdown(brief_json),
        brief_json=brief_json,
        prompt_pack_json=prompt_pack,
    )
    project.status = InfographicProjectStatus.DESIGN_PROMPT_READY.value
    db.add(brief)
    db.add(project)
    db.commit()
    db.refresh(brief)
    return brief


def _resolve_research(
    db: Session,
    project: InfographicProject,
    source_task: ContentTask | None,
) -> ContentResearchReport | None:
    if project.source_research_report_id:
        return db.get(ContentResearchReport, project.source_research_report_id)
    if source_task is None:
        return None
    stmt = (
        select(ContentResearchReport)
        .where(ContentResearchReport.task_id == source_task.id)
        .order_by(ContentResearchReport.created_at.desc(), ContentResearchReport.id.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def _latest_data_pack(db: Session, project_id: str) -> InfographicDataPack | None:
    stmt = (
        select(InfographicDataPack)
        .where(InfographicDataPack.project_id == project_id)
        .order_by(InfographicDataPack.created_at.desc(), InfographicDataPack.id.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def _build_data_pack(
    project: InfographicProject,
    product: Product | None,
    source_task: ContentTask | None,
    research: ContentResearchReport | None,
    pain_profile: Any | None,
) -> dict[str, Any]:
    subject = product.title if product else project.title
    sources = _sources(product, research)
    internal_source_id = "internal-product-data"
    pain_json = pain_profile.profile_json if pain_profile is not None else None
    specs = _specs(product, internal_source_id)
    missing = _missing_fields(product, research, pain_json)
    snapshot_date = datetime.now(UTC).date().isoformat()

    return {
        "schema_version": "1.0",
        "scope": {
            "type": project.scope_type,
            "id": project.scope_id,
            "title": subject,
            "market": "Ukraine ecommerce",
            "snapshot_date": snapshot_date,
            "target_channel": project.target_channel,
        },
        "main_subject": {
            "name": subject,
            "brand": product.brand if product else None,
            "model": product.model if product else None,
            "category": product.category if product else None,
            "price": _price(product, internal_source_id),
            "specs": specs,
            "availability": _fact(product.availability, internal_source_id) if product else None,
            "source_url": product.source_url if product else None,
        },
        "pain_profile": _pain_summary(pain_json),
        "product_card_extraction": _product_card_extraction(product, specs),
        "research_query_plan": _research_query_plan(project, product, pain_json),
        "content_placement_plan": _content_placement_plan(project),
        "pictogram_system": _pictogram_system(project, product, pain_json),
        "brand_style_block": project.brand_style_json or _default_brand_style(),
        "market_position": _market_position_stub(product),
        "competitors": [],
        "buyer_scores": _buyer_scores(pain_json),
        "visualization_candidates": _visualization_candidates(project),
        "claims": _claims(product, pain_json, internal_source_id),
        "sources": sources,
        "source_task_id": source_task.id if source_task else None,
        "source_research_report_id": research.id if research else None,
        "missing_or_risky_data": missing,
    }


def _sources(product: Product | None, research: ContentResearchReport | None) -> list[dict[str, Any]]:
    sources = [
        {
            "id": "internal-product-data",
            "title": product.title if product else "Internal infographic project data",
            "url": product.source_url if product else None,
            "publisher": "local catalog",
            "captured_at": datetime.now(UTC).isoformat(),
        }
    ]
    if research is None:
        return sources
    for index, source in enumerate(research.sources_json or [], start=1):
        sources.append(
            {
                "id": f"r{index}",
                "title": source.get("title") or f"Research source {index}",
                "url": source.get("url"),
                "publisher": source.get("source_type") or "research",
                "captured_at": research.created_at.isoformat(),
            }
        )
    return sources


def _specs(product: Product | None, source_id: str) -> list[dict[str, Any]]:
    if product is None:
        return []
    raw = product.raw_description or ""
    specs = []
    for name, value in [
        ("brand", product.brand),
        ("model", product.model),
        ("category", product.category),
        ("sku", product.sku),
        ("availability", product.availability),
    ]:
        if value:
            specs.append({"name": name, "value": value, "source_id": source_id, "confidence": "high"})
    if raw:
        specs.append(
            {
                "name": "raw_product_description",
                "value": raw[:700],
                "source_id": source_id,
                "confidence": "medium",
            }
        )
    return specs


def _price(product: Product | None, source_id: str) -> dict[str, Any] | None:
    if product is None or product.price is None:
        return None
    return {
        "value": _decimal_to_float(product.price),
        "currency": product.currency,
        "source_id": source_id,
        "captured_at": datetime.now(UTC).isoformat(),
    }


def _fact(value: str | None, source_id: str) -> dict[str, str] | None:
    if not value:
        return None
    return {"value": value, "source_id": source_id, "confidence": "high"}


def _pain_summary(pain_json: dict[str, Any] | None) -> dict[str, Any]:
    if not pain_json:
        return {
            "status": "missing",
            "summary": "No approved pain_profile is linked yet.",
            "confidence": "low",
            "required_before_headline": True,
        }
    primary = pain_json.get("primary_pain") or {}
    return {
        "status": "approved",
        "summary": primary.get("summary"),
        "confidence": primary.get("confidence"),
        "buyer_words": primary.get("buyer_words") or [],
        "proof_map": pain_json.get("proof_map") or [],
        "do_not_claim": pain_json.get("do_not_claim") or [],
    }


def _product_card_extraction(product: Product | None, specs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "fields_to_extract": [
            "title",
            "brand",
            "model",
            "category",
            "price",
            "availability",
            "source_url",
            "raw_description",
            "spec table",
            "warranty",
            "kit contents",
            "dimensions",
            "compatibility",
        ],
        "confirmed_fields": [spec["name"] for spec in specs],
        "extraction_notes": [
            "Use product-card text as an internal source, not as proof for external market claims.",
            "Parse numbers and units only when they are explicit in the card.",
            "Keep absent warranty, ratings, certificates and reviews as missing data.",
        ],
        "raw_description_chars": len(product.raw_description or "") if product else 0,
    }


def _research_query_plan(
    project: InfographicProject,
    product: Product | None,
    pain_json: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    subject = product.title if product else project.title
    category = product.category if product and product.category else project.scope_type
    pain = ((pain_json or {}).get("primary_pain") or {}).get("summary") or "buyer decision problem"
    return [
        {
            "query_type": "product_card_data_extraction",
            "query": f"extract structured specs price availability warranty kit compatibility from {subject}",
            "purpose": "Build factual product-card infographic blocks and pictograms.",
            "target_material": "product_card",
        },
        {
            "query_type": "image_infographic_context",
            "query": f"{subject} {category} visual comparison key specs buyer pain proof map",
            "purpose": "Find what information should become image labels, callouts and source notes.",
            "target_material": "image_asset",
        },
        {
            "query_type": "article_placement",
            "query": f"{category} buyer guide criteria mistakes comparison infographic article sections",
            "purpose": "Decide where infographics belong inside SEO/AEO article structure.",
            "target_material": "seo_article",
        },
        {
            "query_type": "video_presentation",
            "query": f"{subject} {pain} short video storyboard infographic overlay data points",
            "purpose": "Prepare visual beats for product presentation, Shorts and video infographic scenes.",
            "target_material": "video_presentation",
        },
    ]


def _content_placement_plan(project: InfographicProject) -> list[dict[str, Any]]:
    return [
        {
            "material": "product_card",
            "placement": "after short answer / before detailed specifications",
            "slot": "{{infographic:comparison}}",
            "role": "Help buyer understand the product's position and strongest proof points quickly.",
        },
        {
            "material": "seo_article",
            "placement": "after the first buyer-problem section and before criteria comparison",
            "slot": "{{infographic:buyer-guide}}",
            "role": "Turn research findings into a decision map with cited criteria and footnotes.",
        },
        {
            "material": "video_presentation",
            "placement": "scene 2-4 overlay sequence",
            "slot": "storyboard.infographic_overlay",
            "role": "Use the same data blocks as motion overlays; keep exact numbers in editable overlay text.",
        },
        {
            "material": "shorts",
            "placement": "first 3 seconds hook plus one proof strip",
            "slot": "shorts.pain_to_proof_strip",
            "role": "Show the buyer pain and one verified proof point without overloading the frame.",
        },
        {
            "material": "viber_digest",
            "placement": "only when trend or price movement is significant",
            "slot": "viber.compact_trend_card",
            "role": "Send compact, source-backed signal instead of full infographic.",
        },
    ]


def _pictogram_system(
    project: InfographicProject,
    product: Product | None,
    pain_json: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    category = (product.category or "").lower() if product else ""
    base = [
        {
            "key": "pain",
            "label": "Pain",
            "meaning": "Buyer problem or decision tension.",
            "visual_metaphor": "alert badge with restrained contrast",
        },
        {
            "key": "proof",
            "label": "Proof",
            "meaning": "Feature/spec/source that supports the claim.",
            "visual_metaphor": "checkmark inside document badge",
        },
        {
            "key": "price",
            "label": "Price",
            "meaning": "Price point or market position.",
            "visual_metaphor": "price tag with mini bar",
        },
        {
            "key": "missing_data",
            "label": "Needs review",
            "meaning": "Data is incomplete or risky for public claim.",
            "visual_metaphor": "dotted outline info badge",
        },
    ]
    if "солнеч" in category or "solar" in category:
        base.append(
            {
                "key": "autonomy",
                "label": "Autonomy",
                "meaning": "Charging away from a wall outlet.",
                "visual_metaphor": "sun plus battery line icon",
            }
        )
    if pain_json:
        base.append(
            {
                "key": "pain_to_proof",
                "label": "Pain to proof",
                "meaning": "Connect approved pain_profile to verified product facts.",
                "visual_metaphor": "two-step arrow from problem badge to proof badge",
            }
        )
    return base


def _market_position_stub(product: Product | None) -> dict[str, Any]:
    return {
        "group_name": product.category if product else None,
        "price_min": None,
        "price_median": None,
        "price_avg": None,
        "price_max": None,
        "position_label": "needs_market_data",
        "relative_to_median_pct": None,
        "rank_estimate": None,
        "notes": [
            "Connect price_group market indexes before showing market-position claims.",
            "Until competitor prices are collected, use product facts and buyer-guide blocks.",
        ],
    }


def _buyer_scores(pain_json: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not pain_json:
        return [
            {
                "scenario": "Needs confirmed pain profile",
                "score": None,
                "max_score": 10,
                "rationale": "Generate and approve pain_profile before scoring buyer-fit.",
                "source_ids": [],
            }
        ]
    primary = pain_json.get("primary_pain") or {}
    return [
        {
            "scenario": primary.get("summary") or "Approved buyer problem",
            "score": 7,
            "max_score": 10,
            "rationale": "Draft score based on approved pain_profile; requires human review before publishing.",
            "source_ids": primary.get("source_ids") or [],
        }
    ]


def _visualization_candidates(project: InfographicProject) -> list[dict[str, Any]]:
    return [
        {
            "type": "pain_to_proof_map",
            "title": "Buyer pain mapped to product proof",
            "data_refs": ["pain_profile", "main_subject.specs"],
            "unit": None,
        },
        {
            "type": "feature_matrix",
            "title": "What to verify before purchase",
            "data_refs": ["main_subject.specs", "missing_or_risky_data"],
            "unit": None,
        },
        {
            "type": "placement_strip",
            "title": f"Where this infographic fits in {project.target_channel}",
            "data_refs": ["content_placement_plan"],
            "unit": None,
        },
    ]


def _claims(
    product: Product | None,
    pain_json: dict[str, Any] | None,
    source_id: str,
) -> list[dict[str, Any]]:
    claims = []
    if product and product.price is not None:
        claims.append(
            {
                "claim": f"Current internal catalog price is {_decimal_to_float(product.price)} {product.currency or ''}".strip(),
                "claim_type": "fact",
                "source_ids": [source_id],
                "confidence": "high",
            }
        )
    if pain_json:
        primary = pain_json.get("primary_pain") or {}
        claims.append(
            {
                "claim": primary.get("summary"),
                "claim_type": "approved_pain_profile",
                "source_ids": primary.get("source_ids") or [],
                "confidence": primary.get("confidence") or "low",
            }
        )
    return [claim for claim in claims if claim.get("claim")]


def _missing_fields(
    product: Product | None,
    research: ContentResearchReport | None,
    pain_json: dict[str, Any] | None,
) -> list[dict[str, str]]:
    missing = []
    if not pain_json:
        missing.append(
            {
                "field": "approved pain_profile",
                "reason": "Infographic headline should not be pain-led until pain profile is approved.",
                "action": "generate_and_approve_pain_profile",
            }
        )
    if research is None:
        missing.append(
            {
                "field": "external source corpus",
                "reason": "No linked research report for competitor/category claims.",
                "action": "run_deep_research_or_tavily_source_collection",
            }
        )
    if product is not None:
        for field in ["brand", "model", "price", "availability", "raw_description"]:
            if getattr(product, field) in (None, ""):
                missing.append(
                    {
                        "field": field,
                        "reason": "Product card does not contain this field.",
                        "action": "extract_from_card_or_mark_unknown",
                    }
                )
    return missing


def _confidence_score(data_pack: dict[str, Any]) -> float:
    missing_count = len(data_pack.get("missing_or_risky_data") or [])
    source_count = len(data_pack.get("sources") or [])
    score = 0.45 + min(source_count, 4) * 0.1 - min(missing_count, 5) * 0.05
    return round(max(0.1, min(score, 0.95)), 2)


def _build_design_brief_json(
    project: InfographicProject,
    data_pack: dict[str, Any],
) -> dict[str, Any]:
    style = data_pack["brand_style_block"]
    return {
        "headline_insight": _headline(project, data_pack),
        "target_channel": project.target_channel,
        "infographic_type": project.infographic_type,
        "dimensions": _dimensions(project.target_channel),
        "visual_hierarchy": [
            "Headline with decision problem",
            "Pain-to-proof strip",
            "Product facts / feature matrix",
            "Placement-specific callout",
            "Source footnotes and missing-data notes",
        ],
        "required_blocks": [
            {"key": "headline", "role": "State the decision question, not an unsupported claim."},
            {"key": "pain_to_proof", "role": "Map approved pain to product facts."},
            {"key": "facts", "role": "Show specs and price only with source ids."},
            {"key": "pictograms", "role": "Use consistent pictograms from pictogram_system."},
            {"key": "footnotes", "role": "Show snapshot date and source ids."},
        ],
        "chart_specs": data_pack["visualization_candidates"],
        "table_specs": [
            {
                "title": "Product facts requiring review",
                "columns": ["field", "value", "source", "confidence"],
                "data_ref": "main_subject.specs",
            }
        ],
        "pictogram_system": data_pack["pictogram_system"],
        "style": style,
        "footnote_requirements": [
            "Every numeric value must keep source_id.",
            "Show snapshot date from data_pack.scope.snapshot_date.",
            "Missing or risky data must remain visible.",
        ],
        "do_not_claim": (data_pack.get("pain_profile") or {}).get("do_not_claim") or [],
    }


def _build_prompt_pack(
    project: InfographicProject,
    data_pack: dict[str, Any],
    brief_json: dict[str, Any],
) -> dict[str, Any]:
    data_json = json.dumps(data_pack, ensure_ascii=False, indent=2)
    brief_json_text = json.dumps(brief_json, ensure_ascii=False, indent=2)
    return {
        "browser_design_prompt": "\n".join(
            [
                "Create an editable ecommerce infographic from the strict data below.",
                "Do not add new facts, prices, brands, ratings, awards, percentages, sources or claims.",
                f"Output: editable HTML/CSS/SVG. Channel: {project.target_channel}.",
                f"Dimensions: {brief_json['dimensions']['width']}x{brief_json['dimensions']['height']}.",
                "Use the brand_style_block exactly as a style system.",
                "Use pictograms only as simple editable symbols with labels.",
                "Keep source footnotes readable and tied to source ids.",
                "",
                "DATA PACK:",
                data_json,
                "",
                "DESIGN BRIEF:",
                brief_json_text,
            ]
        ),
        "qa_prompt": "\n".join(
            [
                "Check the infographic artifact against the data pack.",
                "Fail if it invents numbers, prices, specs, logos, ratings or unsupported buyer pain.",
                "Verify footnotes, source ids, labels, units, snapshot date, readability and no overlap.",
                "Return JSON with qa_status, blocking_issues, non_blocking_issues and fix_prompt.",
            ]
        ),
        "revision_prompt": (
            "Revise only the QA issues. Preserve all data, source ids, snapshot date, "
            "brand_style_block and pictogram meanings. Do not introduce new facts."
        ),
        "cms_export_prompt": (
            "Prepare alt text, caption, source note, CMS block title, social caption and Viber "
            "digest text using only approved data_pack claims."
        ),
    }


def _design_brief_markdown(brief: dict[str, Any]) -> str:
    blocks = "\n".join(f"- {block['key']}: {block['role']}" for block in brief["required_blocks"])
    pictograms = "\n".join(
        f"- {item['key']}: {item['label']} - {item['meaning']}"
        for item in brief["pictogram_system"]
    )
    return "\n".join(
        [
            f"# Infographic Design Brief: {brief['headline_insight']}",
            "",
            f"- Type: {brief['infographic_type']}",
            f"- Channel: {brief['target_channel']}",
            f"- Size: {brief['dimensions']['width']}x{brief['dimensions']['height']}",
            "",
            "## Required Blocks",
            blocks,
            "",
            "## Pictogram System",
            pictograms,
            "",
            "## Source Rules",
            "- Keep all source ids visible.",
            "- Mark missing data instead of inventing it.",
            "- Do not make claims stronger than the data pack.",
        ]
    )


def _headline(project: InfographicProject, data_pack: dict[str, Any]) -> str:
    pain = data_pack.get("pain_profile") or {}
    if pain.get("status") == "approved" and pain.get("summary"):
        return f"How {data_pack['main_subject']['name']} addresses the buyer decision problem"
    return f"What to verify before using {project.title} in marketing materials"


def _dimensions(channel: str) -> dict[str, int]:
    if channel in {"shorts", "reels", "tiktok"}:
        return {"width": 1080, "height": 1920}
    if channel in {"viber", "social"}:
        return {"width": 1080, "height": 1350}
    if channel == "product_card":
        return {"width": 1200, "height": 900}
    return {"width": 1280, "height": 720}


def _default_brand_style() -> dict[str, Any]:
    return {
        "name": "Electronics ecommerce clean system",
        "palette": {
            "background": "#F7F8FA",
            "surface": "#FFFFFF",
            "ink": "#1F2933",
            "muted": "#64748B",
            "accent": "#0F766E",
            "warning": "#B45309",
            "line": "#CBD5E1",
        },
        "typography": {
            "heading": "Inter or Arial",
            "body": "Inter or Arial",
            "label_case": "sentence",
        },
        "shape": {"radius_px": 8, "stroke_width_px": 1},
        "layout": {
            "grid": "12-column editorial grid",
            "density": "scan-friendly, no decorative clutter",
            "footnotes": "visible and readable, never tiny legal dust",
        },
    }


def _decimal_to_float(value: Decimal) -> float:
    return float(value)
