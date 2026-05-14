from app.adapters.storage import StorageAdapter, StoredObject


class MockStorageAdapter(StorageAdapter):
    provider = "mock-storage"

    def __init__(self) -> None:
        self._objects: dict[str, str] = {}

    def put_text(self, key: str, content: str, content_type: str = "text/plain") -> StoredObject:
        self._objects[key] = content
        return StoredObject(
            bucket="mock",
            key=key,
            url=f"mock://storage/{key}",
            content_type=content_type,
        )

    def get_text(self, key: str) -> str:
        return self._objects[key]
