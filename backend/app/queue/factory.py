from app.config import Settings
from app.queue.base import TaskQueue
from app.queue.rq_queue import RQTaskQueue
from app.queue.sync_queue import SyncTaskQueue


def build_task_queue(settings: Settings) -> TaskQueue:
    if settings.app_env == "test" or settings.queue_mode == "sync":
        return SyncTaskQueue()
    return RQTaskQueue(settings)
