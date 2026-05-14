from app.adapters.cms import CMSAdapter, PublishRequest, PublishResult


class MockCMSAdapter(CMSAdapter):
    provider = "mock-cms"

    def prepare_payload(self, request: PublishRequest) -> dict:
        slug = request.title.lower().strip().replace(" ", "-")[:80] or "untitled"
        return {
            "provider": self.provider,
            "destination": request.destination_type,
            "operation": "create_draft",
            "slug": slug,
            "status": request.status,
            "post": {
                "title": request.title,
                "content_html": request.body_html,
                "content_markdown": request.body_markdown,
                "meta_title": request.meta_title,
                "meta_description": request.meta_description,
            },
            "schema_json": request.schema_json,
            "product_card_json": request.product_card_json,
            "media_assets_json": request.media_assets_json,
            "safety": {
                "dry_run": True,
                "real_publish_required_flag": "ENABLE_REAL_PUBLISHING=true",
            },
        }

    def publish(self, request: PublishRequest) -> PublishResult:
        slug = request.title.lower().strip().replace(" ", "-")[:80] or "untitled"
        return PublishResult(
            provider=self.provider,
            external_id=f"mock-{slug}",
            url=f"https://example.com/{slug}",
            status=request.status,
            raw={
                "title": request.title,
                "meta_title": request.meta_title,
                "has_schema": request.schema_json is not None,
                "has_product_card": request.product_card_json is not None,
            },
        )
