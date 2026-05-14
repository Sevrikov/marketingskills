from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class StoredObject:
    bucket: str
    key: str
    url: str
    content_type: str | None = None


class StorageAdapter(ABC):
    @abstractmethod
    def put_text(self, key: str, content: str, content_type: str = "text/plain") -> StoredObject:
        """Store a text object."""

    @abstractmethod
    def get_text(self, key: str) -> str:
        """Read a text object."""
