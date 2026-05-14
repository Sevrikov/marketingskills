import base64
from typing import Any

from app.adapters.gemini import GeminiConfigurationError
from app.adapters.image_generation import (
    ImageGenerationAdapter,
    ImageGenerationRequest,
    ImageGenerationResult,
)
from app.config import Settings
from app.services.gemini_quota import GeminiQuotaGovernor, build_gemini_candidates


class GeminiImageGenerationAdapter(ImageGenerationAdapter):
    provider = "google-gemini-image"

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.settings = settings
        self._client = client

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        if not self.settings.enable_real_image_generation and self._client is None:
            raise GeminiConfigurationError(
                "Real image generation is disabled. Set ENABLE_REAL_IMAGE_GENERATION=true."
            )
        if not self.settings.google_api_key and self._client is None:
            raise GeminiConfigurationError(
                "GOOGLE_API_KEY is not configured. Add it to local .env, never to git."
            )

        client = self._client or self._build_client()
        config = self._build_config()
        model_candidates = build_gemini_candidates(
            self.settings.gemini_image_model,
            self.settings.gemini_image_models,
        )
        quota = GeminiQuotaGovernor(self.settings)
        errors: list[Exception] = []
        while model_candidates:
            model = quota.select_model(model_candidates)
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=[request.prompt],
                    config=config,
                )
            except Exception as exc:
                quota.record_failure(model, exc)
                errors.append(exc)
                model_candidates = [candidate for candidate in model_candidates if candidate != model]
                if model_candidates:
                    continue
                raise

            image_part = _first_inline_image_part(response)
            if image_part is None:
                raise GeminiConfigurationError("Gemini response did not include an image part.")

            mime_type = _inline_mime_type(image_part) or "image/png"
            image_data = _inline_data_bytes(image_part)
            storage_uri = f"data:{mime_type};base64,{base64.b64encode(image_data).decode('ascii')}"
            quota.record_success(model, input_chars=len(request.prompt), output_chars=0)
            return ImageGenerationResult(
                provider=self.provider,
                storage_uri=storage_uri,
                model=model,
                prompt=request.prompt,
                metadata={
                    "asset_id": request.asset_id,
                    "slot": request.slot,
                    "asset_type": request.asset_type,
                    "mime_type": mime_type,
                    "response_type": type(response).__name__,
                    "inline_bytes": len(image_data),
                    "dimensions": request.dimensions,
                },
            )

        if errors:
            raise errors[-1]
        raise GeminiConfigurationError("No Gemini image model candidate was available.")

    def _build_client(self) -> Any:
        try:
            from google import genai
        except ImportError as exc:
            raise GeminiConfigurationError(
                "google-genai package is not installed in the current runtime."
            ) from exc

        return genai.Client(api_key=self.settings.google_api_key)

    def _build_config(self) -> Any:
        try:
            from google.genai import types
        except ImportError as exc:
            raise GeminiConfigurationError(
                "google-genai package is not installed in the current runtime."
            ) from exc

        return types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"])


def _first_inline_image_part(response: Any) -> Any | None:
    for part in getattr(response, "parts", None) or []:
        if getattr(part, "inline_data", None) is not None:
            return part
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            if getattr(part, "inline_data", None) is not None:
                return part
    return None


def _inline_mime_type(part: Any) -> str | None:
    inline_data = getattr(part, "inline_data", None)
    return getattr(inline_data, "mime_type", None) or getattr(inline_data, "mimeType", None)


def _inline_data_bytes(part: Any) -> bytes:
    inline_data = getattr(part, "inline_data", None)
    data = getattr(inline_data, "data", b"")
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        try:
            return base64.b64decode(data)
        except Exception:
            return data.encode("utf-8")
    return bytes(data)
