import html
from urllib.parse import quote

from app.adapters.image_generation import (
    ImageGenerationAdapter,
    ImageGenerationRequest,
    ImageGenerationResult,
)


class MockImageGenerationAdapter(ImageGenerationAdapter):
    provider = "mock-image"

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        label = request.slot.replace(":", " / ")
        subtitle = request.dimensions or "article asset"
        svg = "\n".join(
            [
                '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675">',
                '<rect width="1200" height="675" fill="#f3f7fa"/>',
                '<rect x="60" y="60" width="1080" height="555" rx="24" fill="#ffffff" stroke="#8aa4b8" stroke-width="4" stroke-dasharray="18 14"/>',
                '<circle cx="600" cy="270" r="74" fill="#d9e8f3"/>',
                '<path d="M548 300h104l-30-42-20 24-18-20z" fill="#4d7f9f"/>',
                f'<text x="600" y="405" text-anchor="middle" font-family="Arial, sans-serif" font-size="42" font-weight="700" fill="#243746">{html.escape(label)}</text>',
                f'<text x="600" y="458" text-anchor="middle" font-family="Arial, sans-serif" font-size="25" fill="#5f7280">{html.escape(subtitle)}</text>',
                '<text x="600" y="516" text-anchor="middle" font-family="Arial, sans-serif" font-size="20" fill="#789">mock generated image placeholder</text>',
                "</svg>",
            ]
        )
        return ImageGenerationResult(
            provider=self.provider,
            storage_uri=f"data:image/svg+xml;charset=utf-8,{quote(svg)}",
            model="mock-svg-placeholder",
            prompt=request.prompt,
            metadata={
                "asset_id": request.asset_id,
                "slot": request.slot,
                "asset_type": request.asset_type,
                "dimensions": request.dimensions,
                "safe_placeholder": True,
            },
        )
