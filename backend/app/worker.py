from redis import Redis
from rq import Worker

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    worker = Worker(["content_tasks"], connection=redis)
    print(f"Worker started for {settings.app_name} in {settings.app_env} mode")
    worker.work()


if __name__ == "__main__":
    main()
