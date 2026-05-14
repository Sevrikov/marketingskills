from redis import Redis
from rq import Queue

from app.config import Settings
from app.queue.base import EnqueuedJob, TaskQueue


class RQTaskQueue(TaskQueue):
    queue_name = "content_tasks"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.redis = Redis.from_url(settings.redis_url)
        self.queue = Queue(self.queue_name, connection=self.redis)

    def enqueue_content_task(self, task_id: str) -> EnqueuedJob:
        job = self.queue.enqueue(
            "app.worker_jobs.process_content_task",
            task_id,
            job_timeout=900,
            result_ttl=86400,
            failure_ttl=86400,
        )
        return EnqueuedJob(id=job.id, queue_name=self.queue_name, task_id=task_id)
