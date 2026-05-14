from app.adapters.llm import LLMAdapter, LLMRequest, LLMResponse
from app.config import Settings
from app.services.gemini_quota import (
    GeminiQuotaGovernor,
    build_gemini_candidates,
    should_try_next_gemini_model,
)


class GeminiConfigurationError(RuntimeError):
    """Raised when Gemini is requested but not configured."""


class GeminiLLMAdapter(LLMAdapter):
    provider = "google-gemini"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_text(self, request: LLMRequest) -> LLMResponse:
        if not self.settings.google_api_key:
            raise GeminiConfigurationError(
                "GOOGLE_API_KEY is not configured. Add it to local .env, never to git."
            )

        try:
            from google import genai
        except ImportError as exc:
            raise GeminiConfigurationError(
                "google-genai package is not installed in the current runtime."
            ) from exc

        model_candidates = build_gemini_candidates(
            request.model or self.settings.gemini_content_model,
            self.settings.gemini_smoke_models,
        )
        quota = GeminiQuotaGovernor(self.settings)
        client = genai.Client(api_key=self.settings.google_api_key)

        prompt = request.prompt
        if request.system_prompt:
            prompt = f"{request.system_prompt}\n\n{request.prompt}"

        errors: list[Exception] = []
        while model_candidates:
            model = quota.select_model(model_candidates)
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
            except Exception as exc:
                quota.record_failure(model, exc)
                errors.append(exc)
                model_candidates = [candidate for candidate in model_candidates if candidate != model]
                if should_try_next_gemini_model(exc) and model_candidates:
                    continue
                raise

            text = response.text or ""
            quota.record_success(model, input_chars=len(prompt), output_chars=len(text))
            return LLMResponse(
                text=text,
                model=model,
                provider=self.provider,
                raw={"response_type": type(response).__name__},
            )

        if errors:
            raise errors[-1]
        raise GeminiConfigurationError("No Gemini model candidate was available.")
