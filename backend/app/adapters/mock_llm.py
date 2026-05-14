from app.adapters.llm import LLMAdapter, LLMRequest, LLMResponse


class MockLLMAdapter(LLMAdapter):
    provider = "mock"

    def generate_text(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=f"[MOCK RESPONSE]\n\nPrompt received:\n{request.prompt}",
            model=request.model or "mock-model",
            provider=self.provider,
            raw=None,
        )
