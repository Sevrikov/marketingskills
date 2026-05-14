import os
import re
from uuid import uuid4
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.content_tasks import get_task_queue
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (  # noqa: F401
    agent_skill,
    article_asset,
    article_review_checkpoint,
    content_draft,
    content_opportunity,
    content_research_report,
    content_task,
    infographic_data_pack,
    infographic_design_brief,
    infographic_project,
    media_brief,
    market_digest_batch,
    monitored_source,
    notification_policy,
    pain_profile,
    price_change_event,
    price_group,
    price_market_index,
    price_snapshot,
    price_trend_event,
    product,
    product_content_profile,
    prompt_template,
    publish_package,
    publication_preview,
    runtime_setting,
    scheduled_job,
    scheduled_job_run,
    task_event,
)
from app.queue.base import EnqueuedJob, TaskQueue


@pytest.fixture()
def tmp_path(request) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", request.node.name)
    path = Path(__file__).resolve().parents[1] / ".tmp" / "test-paths" / f"{safe_name}-{uuid4().hex}"
    os.makedirs(path, exist_ok=True)
    return path


class FakeTaskQueue(TaskQueue):
    def __init__(self) -> None:
        self.enqueued_task_ids: list[str] = []

    def enqueue_content_task(self, task_id: str) -> EnqueuedJob:
        self.enqueued_task_ids.append(task_id)
        return EnqueuedJob(id=f"fake-{task_id}", queue_name="fake", task_id=task_id)


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    def override_get_db():
        yield db_session

    fake_queue = FakeTaskQueue()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_task_queue] = lambda: fake_queue
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
