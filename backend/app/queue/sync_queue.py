from app.queue.base import EnqueuedJob, TaskQueue
from app.worker_jobs import process_content_task


class SyncTaskQueue(TaskQueue):
    queue_name = "sync"

    def enqueue_content_task(self, task_id: str) -> EnqueuedJob:
        process_content_task(task_id)
        return EnqueuedJob(id=f"sync-{task_id}", queue_name=self.queue_name, task_id=task_id)
