import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.media_brief import MediaBrief
from app.models.publish_package import PublishPackage
from app.services.content_tasks import log_task_event


class PackageNotReadyForMediaBrief(ValueError):
    pass


def create_media_brief(db: Session, package: PublishPackage) -> MediaBrief:
    if package.status != "ready":
        raise PackageNotReadyForMediaBrief(
            f"Publish package must be ready, current status is {package.status}."
        )

    brief_json = build_media_brief_json(package)
    markdown = build_media_brief_markdown(brief_json)
    media_brief = MediaBrief(
        package_id=package.id,
        brief_type="video_brief_pack",
        status="brief_ready",
        markdown=markdown,
        brief_json=brief_json,
    )
    db.add(media_brief)
    db.flush()
    log_task_event(
        db,
        package.task,
        event_type="media_brief_created",
        from_status=package.task.status,
        to_status=package.task.status,
        step="media_brief",
        message=f"Video/media brief prepared for package {package.slug}.",
        metadata_json={
            "package_id": package.id,
            "media_brief_id": media_brief.id,
            "brief_type": media_brief.brief_type,
            "formats": [item["format"] for item in brief_json["deliverables"]],
            "veo_generation_enabled": False,
        },
    )
    db.commit()
    db.refresh(media_brief)
    return media_brief


def list_media_briefs(db: Session, package_id: str) -> list[MediaBrief]:
    stmt = (
        select(MediaBrief)
        .where(MediaBrief.package_id == package_id)
        .order_by(MediaBrief.created_at.asc(), MediaBrief.id.asc())
    )
    return list(db.scalars(stmt))


def build_media_brief_json(package: PublishPackage) -> dict[str, Any]:
    package_json = package.package_json
    task = package_json.get("task", {})
    content = package_json.get("content", {})
    research = package_json.get("research", {})
    markdown = content.get("markdown") or package.markdown
    key_message = _first_sentence(markdown) or package.title
    cta = _cta_for_task(task.get("task_type"))
    required_facts = _required_facts(package, research)
    pain_profile = _pain_profile_from_package(markdown, research)
    forbidden_claims = [
        "Do not invent prices, discounts, warranties or delivery terms.",
        "Do not claim official certifications unless present in source data.",
        "Do not exaggerate customer pain or promise unsupported outcomes.",
        "Do not start Veo/video generation before human approval of this brief.",
    ]
    return {
        "package": {
            "id": package.id,
            "slug": package.slug,
            "title": package.title,
        },
        "source_task": {
            "id": task.get("id"),
            "task_type": task.get("task_type"),
            "language": task.get("language") or "ru",
            "topic": task.get("topic"),
        },
        "skill": {
            "name": "ecommerce-video-brief",
            "version": "0.1.0",
        },
        "goal": "Turn approved ecommerce content into safe video production briefs.",
        "audience": "Electronics ecommerce buyers comparing products and use cases.",
        "key_message": key_message,
        "pain_profile": pain_profile,
        "offer": "Use only approved commercial offer data from the publish package.",
        "cta": cta,
        "required_facts": required_facts,
        "forbidden_claims": forbidden_claims,
        "tone": "clear, practical, trustworthy, marketing-focused",
        "subtitle_requirements": {
            "required": True,
            "language": task.get("language") or "ru",
            "style": "short readable captions, no dense paragraphs",
        },
        "deliverables": [
            _long_youtube_brief(package, key_message, cta, required_facts),
            _short_vertical_brief(package, key_message, cta, required_facts),
            _veo_prompt_pack(package, key_message, cta, required_facts),
        ],
        "safety": {
            "dry_run": True,
            "real_video_generation_enabled": False,
            "real_video_generation_required_flag": "ENABLE_REAL_VIDEO_GENERATION=true",
        },
    }


def build_media_brief_markdown(brief_json: dict[str, Any]) -> str:
    lines = [
        f"# Media Brief: {brief_json['package']['title']}",
        "",
        f"- Goal: {brief_json['goal']}",
        f"- Audience: {brief_json['audience']}",
        f"- Key message: {brief_json['key_message']}",
        f"- CTA: {brief_json['cta']}",
        f"- Tone: {brief_json['tone']}",
        "",
        "## Required Facts",
        *[f"- {fact}" for fact in brief_json["required_facts"]],
        "",
        "## Customer Pain Profile",
        f"- Primary pain: {brief_json['pain_profile']['primary_pain']}",
        f"- Confidence: {brief_json['pain_profile']['confidence']}",
        f"- Usage: {brief_json['pain_profile']['usage_note']}",
        "",
        "## Forbidden Claims",
        *[f"- {claim}" for claim in brief_json["forbidden_claims"]],
    ]
    for deliverable in brief_json["deliverables"]:
        lines.extend(
            [
                "",
                f"## {deliverable['platform']} / {deliverable['format']}",
                f"- Duration: {deliverable['duration_seconds']} seconds",
                f"- Aspect ratio: {deliverable['aspect_ratio']}",
                f"- Hook: {deliverable['hook']}",
                f"- CTA: {deliverable['cta']}",
                "",
                "### Scene List",
            ]
        )
        for scene in deliverable["scene_list"]:
            lines.append(
                f"- {scene['timecode']}: {scene['visual']} | VO: {scene['voiceover']}"
            )
        if deliverable.get("veo_prompts"):
            lines.extend(["", "### Veo Prompts"])
            for prompt in deliverable["veo_prompts"]:
                lines.append(f"- {prompt['shot_id']}: {prompt['prompt']}")
    return "\n".join(lines)


def _long_youtube_brief(
    package: PublishPackage,
    key_message: str,
    cta: str,
    required_facts: list[str],
) -> dict[str, Any]:
    return {
        "platform": "YouTube",
        "format": "long_video",
        "duration_seconds": 360,
        "aspect_ratio": "16:9",
        "language": package.package_json.get("task", {}).get("language") or "ru",
        "hook": f"What should buyers know about {package.title} before choosing?",
        "key_message": key_message,
        "cta": cta,
        "required_facts": required_facts,
        "scene_list": [
            _scene("00:00-00:20", "Product/context opener with problem framing", key_message),
            _scene("00:20-01:20", "Main buyer pain points and use cases", "Explain the buyer problem."),
            _scene("01:20-03:30", "Feature and benefit breakdown", "Connect facts to practical outcomes."),
            _scene("03:30-05:20", "Comparison and decision criteria", "Help the viewer decide confidently."),
            _scene("05:20-06:00", "Recap and CTA", cta),
        ],
    }


def _short_vertical_brief(
    package: PublishPackage,
    key_message: str,
    cta: str,
    required_facts: list[str],
) -> dict[str, Any]:
    return {
        "platform": "Shorts/Reels/TikTok",
        "format": "vertical_short",
        "duration_seconds": 35,
        "aspect_ratio": "9:16",
        "language": package.package_json.get("task", {}).get("language") or "ru",
        "hook": f"Before you buy: {package.title}",
        "key_message": key_message,
        "cta": cta,
        "required_facts": required_facts[:4],
        "scene_list": [
            _scene("00:00-00:03", "Fast product/problem hook", "Stop scrolling if this matters to you."),
            _scene("00:03-00:12", "Show strongest buyer benefit", key_message),
            _scene("00:12-00:25", "Three quick proof points", "Use only verified facts."),
            _scene("00:25-00:35", "Offer and CTA frame", cta),
        ],
    }


def _veo_prompt_pack(
    package: PublishPackage,
    key_message: str,
    cta: str,
    required_facts: list[str],
) -> dict[str, Any]:
    scene_list = [
        _scene("shot-01", "Clean ecommerce product hero on neutral desk", key_message),
        _scene("shot-02", "Lifestyle close-up showing practical use case", "Show the benefit visually."),
        _scene("shot-03", "Interface/text overlay space for key facts", "Leave room for subtitles."),
        _scene("shot-04", "Final product and CTA composition", cta),
    ]
    return {
        "platform": "Google Veo",
        "format": "veo_prompt_pack",
        "duration_seconds": 32,
        "aspect_ratio": "16:9 and 9:16 variants",
        "language": package.package_json.get("task", {}).get("language") or "ru",
        "hook": f"Visual product story for {package.title}",
        "key_message": key_message,
        "cta": cta,
        "required_facts": required_facts,
        "scene_list": scene_list,
        "veo_prompts": [
            {
                "shot_id": scene["timecode"],
                "prompt": (
                    f"{scene['visual']}. Ecommerce product video, realistic lighting, "
                    "clean composition, no unverified text claims, leave safe space for captions."
                ),
                "negative_prompt": "distorted product, fake logos, unreadable text, exaggerated claims",
            }
            for scene in scene_list
        ],
    }


def _scene(timecode: str, visual: str, voiceover: str) -> dict[str, str]:
    return {
        "timecode": timecode,
        "visual": visual,
        "voiceover": voiceover,
    }


def _required_facts(package: PublishPackage, research: dict[str, Any]) -> list[str]:
    sources = research.get("sources") or []
    facts = [
        f"Approved package title: {package.title}",
        f"Publish package slug: {package.slug}",
    ]
    for source in sources[:5]:
        title = source.get("title")
        url = source.get("url")
        if title and url:
            facts.append(f"Source: {title} ({url})")
        elif title:
            facts.append(f"Source: {title}")
    return facts


def _pain_profile_from_package(markdown: str, research: dict[str, Any]) -> dict[str, Any]:
    normalized = research.get("normalized") or {}
    explicit_profile = normalized.get("pain_profile")
    if isinstance(explicit_profile, dict):
        return {
            "primary_pain": explicit_profile.get("primary_pain") or "Use approved pain profile.",
            "confidence": explicit_profile.get("confidence") or "unknown",
            "usage_note": "Use only claims present in approved pain_profile.",
            "source": "research.normalized.pain_profile",
        }
    pain_hint = _first_sentence(markdown) or "Customer pain is not explicitly confirmed."
    return {
        "primary_pain": pain_hint,
        "confidence": "low",
        "usage_note": (
            "Treat as a draft pain angle until a dedicated pain_profile is generated "
            "and approved."
        ),
        "source": "publish_package_content",
    }


def _first_sentence(markdown: str) -> str:
    plain = re.sub(r"[#*_`>\[\]]+", " ", markdown)
    plain = re.sub(r"\s+", " ", plain).strip()
    match = re.search(r"(.{40,220}?[.!?])\s", plain)
    if match:
        return match.group(1).strip()
    return plain[:180].strip()


def _cta_for_task(task_type: str | None) -> str:
    if task_type == "product_card":
        return "Open the product page and compare the key specs."
    if task_type == "video_brief":
        return "Approve the brief before video generation."
    return "Open the product page or approved article for details."
