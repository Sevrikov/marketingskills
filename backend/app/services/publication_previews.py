import html
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.cms import CMSAdapter, PublishRequest, PublishResult
from app.config import Settings
from app.models.product_content_profile import ProductContentProfile
from app.models.publication_preview import PublicationPreview
from app.models.publish_package import PublishPackage
from app.services.content_tasks import log_task_event


class PackageNotReadyForPublication(ValueError):
    pass


class PublicationPreviewNotReady(ValueError):
    pass


class RealPublishingDisabled(ValueError):
    pass


class PublicationConfirmationRequired(ValueError):
    pass


class CMSProviderMismatch(ValueError):
    pass


def create_publication_preview(
    db: Session,
    package: PublishPackage,
    adapter: CMSAdapter,
    settings: Settings,
) -> PublicationPreview:
    if package.status != "ready":
        raise PackageNotReadyForPublication(
            f"Publish package must be ready, current status is {package.status}."
        )

    request = build_publish_request(db, package, settings)
    payload = adapter.prepare_payload(request)
    payload["safety"] = {
        **payload.get("safety", {}),
        "dry_run": True,
        "real_publishing_enabled": settings.enable_real_publishing,
    }

    preview = PublicationPreview(
        package_id=package.id,
        provider=adapter.provider,
        destination_type="cms",
        status="dry_run_ready",
        payload_json=payload,
        result_json=None,
    )
    db.add(preview)
    db.flush()
    log_task_event(
        db,
        package.task,
        event_type="publication_preview_created",
        from_status=package.task.status,
        to_status=package.task.status,
        step="publication_preview",
        message=f"CMS dry-run payload prepared for package {package.slug}.",
        metadata_json={
            "package_id": package.id,
            "preview_id": preview.id,
            "provider": adapter.provider,
            "destination_type": "cms",
            "dry_run": True,
        },
    )
    db.commit()
    db.refresh(preview)
    return preview


def get_publication_preview(db: Session, preview_id: str) -> PublicationPreview | None:
    return db.get(PublicationPreview, preview_id)


def list_publication_previews(db: Session, package_id: str) -> list[PublicationPreview]:
    stmt = (
        select(PublicationPreview)
        .where(PublicationPreview.package_id == package_id)
        .order_by(PublicationPreview.created_at.asc(), PublicationPreview.id.asc())
    )
    return list(db.scalars(stmt))


def publish_publication_preview(
    db: Session,
    preview: PublicationPreview,
    adapter: CMSAdapter,
    settings: Settings,
    confirmation_phrase: str | None,
) -> PublicationPreview:
    if preview.status != "dry_run_ready":
        raise PublicationPreviewNotReady(
            f"Publication preview must be dry_run_ready, current status is {preview.status}."
        )
    if not settings.enable_real_publishing:
        raise RealPublishingDisabled(
            "Real publishing is disabled. Set ENABLE_REAL_PUBLISHING=true only after CMS checks."
        )
    if preview.provider != adapter.provider:
        raise CMSProviderMismatch(
            f"Preview provider {preview.provider} does not match active provider {adapter.provider}."
        )

    required_phrase = f"publish:{preview.id}"
    if confirmation_phrase != required_phrase:
        raise PublicationConfirmationRequired(
            f"Confirmation phrase is required: {required_phrase}"
        )

    request = build_publish_request(db, preview.package, settings)
    result = adapter.publish(request)
    preview.status = "published"
    preview.result_json = _result_json(result, settings)
    db.add(preview)
    log_task_event(
        db,
        preview.package.task,
        event_type="publication_published",
        from_status=preview.package.task.status,
        to_status=preview.package.task.status,
        step="publication_publish",
        message=f"CMS publish completed through {adapter.provider}.",
        metadata_json={
            "package_id": preview.package_id,
            "preview_id": preview.id,
            "provider": adapter.provider,
            "external_id": result.external_id,
            "url": result.url,
        },
    )
    db.commit()
    db.refresh(preview)
    return preview


def build_publish_request(
    db: Session,
    package: PublishPackage,
    settings: Settings,
) -> PublishRequest:
    package_json = package.package_json
    content = package_json.get("content", {})
    research = package_json.get("research", {})
    task = package_json.get("task", {})
    markdown = content.get("markdown") or package.markdown
    title = package.title
    sources = research.get("sources") or []
    product_profile = _approved_product_profile_for_package(db, package)
    product_card_json = _product_card_json(product_profile)
    schema_json = _build_schema_json(package, content, research, task, product_profile)
    media_assets = _article_assets_for_package(package)
    body_html = _markdown_to_html(markdown, sources, media_assets)
    return PublishRequest(
        title=title,
        body_html=body_html,
        body_markdown=markdown,
        meta_title=_truncate(title, 60),
        meta_description=_meta_description(markdown),
        schema_json=schema_json,
        product_card_json=product_card_json,
        media_assets_json=media_assets,
        status="draft",
        destination_type=settings.cms_destination_type,
    )


def _build_schema_json(
    package: PublishPackage,
    content: dict[str, Any],
    research: dict[str, Any],
    task: dict[str, Any],
    product_profile: ProductContentProfile | None,
) -> dict[str, Any]:
    sources = research.get("sources") or []
    same_as = [source.get("url") for source in sources if source.get("url")]
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": content.get("title") or package.title,
        "inLanguage": task.get("language"),
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": package.slug,
        },
        "citation": same_as,
        "isAccessibleForFree": True,
    }
    if product_profile is None:
        return article_schema
    product_schema = dict(product_profile.schema_json)
    article_schema["about"] = {
        "@type": "Product",
        "name": product_profile.generated_title,
    }
    article_schema["mainEntity"] = product_schema
    return {
        "@context": "https://schema.org",
        "@graph": [article_schema, product_schema],
    }


def _approved_product_profile_for_package(
    db: Session,
    package: PublishPackage,
) -> ProductContentProfile | None:
    product_id = package.task.product_id
    if not product_id:
        return None
    stmt = (
        select(ProductContentProfile)
        .where(
            ProductContentProfile.product_id == product_id,
            ProductContentProfile.status == "approved",
        )
        .limit(1)
    )
    return db.scalars(stmt).first()


def _product_card_json(profile: ProductContentProfile | None) -> dict[str, Any] | None:
    if profile is None:
        return None
    return {
        "id": profile.id,
        "product_id": profile.product_id,
        "status": profile.status,
        "title": profile.generated_title,
        "short_description": profile.short_description,
        "long_description": profile.long_description,
        "seo_title": profile.seo_title,
        "meta_description": profile.meta_description,
        "specifications": profile.specifications_json,
        "faq": profile.faq_json,
        "schema": profile.schema_json,
        "alt_texts": profile.alt_texts_json,
    }


def _article_assets_for_package(package: PublishPackage) -> list[dict[str, Any]]:
    article_studio = (package.package_json or {}).get("article_studio") or {}
    assets = article_studio.get("assets") or []
    return [
        {
            "id": asset.get("id"),
            "slot": asset.get("slot"),
            "asset_type": asset.get("asset_type"),
            "status": asset.get("status"),
            "storage_uri": asset.get("storage_uri"),
            "alt_text": asset.get("alt_text"),
            "caption": asset.get("caption"),
            "brief_json": asset.get("brief_json"),
            "qa_json": asset.get("qa_json"),
            "cms_insertion": _asset_cms_insertion_state(asset),
        }
        for asset in assets
        if asset.get("slot")
    ]


def _asset_cms_insertion_state(asset: dict[str, Any]) -> str:
    if asset.get("status") != "approved":
        return "placeholder_pending_review"
    storage_uri = asset.get("storage_uri") or ""
    if storage_uri.startswith("mock://"):
        return "placeholder_waiting_upload"
    return "ready"


def _result_json(result: PublishResult, settings: Settings) -> dict[str, Any]:
    return {
        "provider": result.provider,
        "external_id": result.external_id,
        "url": result.url,
        "status": result.status,
        "raw": result.raw or {},
        "safety": {
            "real_publishing_enabled": settings.enable_real_publishing,
            "confirmation_required": True,
            "dry_run": False,
        },
    }


def _markdown_to_html(
    markdown: str,
    sources: list[dict[str, Any]],
    media_assets: list[dict[str, Any]] | None = None,
) -> str:
    blocks = []
    assets_by_token = _assets_by_markdown_token(media_assets or [])
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        asset_html = _asset_placeholder_html(line, assets_by_token)
        if asset_html:
            blocks.append(asset_html)
            continue
        escaped = html.escape(line)
        if line.startswith("### "):
            blocks.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            blocks.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            blocks.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("- "):
            blocks.append(f"<p>{escaped}</p>")
        else:
            blocks.append(f"<p>{escaped}</p>")

    if sources:
        blocks.append("<h2>Sources</h2>")
        for source in sources:
            title = html.escape(source.get("title") or "Source")
            url = source.get("url")
            if url:
                blocks.append(f'<p><a href="{html.escape(url)}" rel="nofollow">{title}</a></p>')
            else:
                blocks.append(f"<p>{title}</p>")
    return "\n".join(blocks)


def _assets_by_markdown_token(media_assets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_token = {}
    for asset in media_assets:
        slot = asset.get("slot") or ""
        if ":" not in slot:
            continue
        asset_type, name = slot.split(":", 1)
        by_token[f"{{{{{asset_type}:{name}}}}}"] = asset
    return by_token


def _asset_placeholder_html(line: str, assets_by_token: dict[str, dict[str, Any]]) -> str | None:
    asset = assets_by_token.get(line)
    if not asset:
        return None
    slot = html.escape(asset.get("slot") or "asset")
    status = html.escape(asset.get("status") or "pending")
    insertion_state = html.escape(asset.get("cms_insertion") or "placeholder_pending_review")
    alt_text = html.escape(asset.get("alt_text") or slot)
    caption = html.escape(asset.get("caption") or "")
    storage_uri = asset.get("storage_uri") or ""
    classes = f"article-asset article-asset-{insertion_state}"
    if insertion_state == "ready":
        media_html = f'<img src="{html.escape(storage_uri)}" alt="{alt_text}" loading="lazy" />'
    else:
        media_html = (
            '<div class="article-asset-placeholder" role="img" '
            f'aria-label="{alt_text}">'
            '<span class="asset-loader"></span>'
            '<strong>Image slot</strong>'
            f'<small>{slot} / {status}</small>'
            "</div>"
        )
    return (
        f'<figure class="{classes}" data-asset-slot="{slot}" data-asset-status="{status}">'
        f"{media_html}"
        f"<figcaption>{caption}</figcaption>"
        "</figure>"
    )


def _meta_description(markdown: str) -> str:
    plain = re.sub(r"[#*_`>\[\]()-]+", " ", markdown)
    plain = re.sub(r"\s+", " ", plain).strip()
    return _truncate(plain, 155)


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "..."
