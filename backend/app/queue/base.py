from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class EnqueuedJob:
    id: str
    queue_name: str
    task_id: str


class TaskQueue(ABC):
    @abstractmethod
    def enqueue_content_task(self, task_id: str) -> EnqueuedJob:
        """Enqueue a content task for background processing."""
