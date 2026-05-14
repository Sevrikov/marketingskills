from app.adapters.media import MediaAdapter, MediaGenerationRequest, MediaGenerationResult


class MockMediaAdapter(MediaAdapter):
    provider = "mock-media"

    def generate(self, request: MediaGenerationRequest) -> MediaGenerationResult:
        external_id = f"mock-{request.media_type}-{request.task_id or 'no-task'}"
        return MediaGenerationResult(
            provider=self.provider,
            media_type=request.media_type,
            status="completed",
            external_id=external_id,
            file_url=f"mock://media/{external_id}",
            metadata={
                "prompt": request.prompt,
                "aspect_ratio": request.aspect_ratio,
            },
        )
