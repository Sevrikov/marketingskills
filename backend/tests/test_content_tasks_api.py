def test_create_topic_task(client):
    response = client.post(
        "/api/tasks",
        json={
            "task_type": "seo_article",
            "language": "ru",
            "topic": "Как выбрать Starlink Mini",
        },
    )

    assert response.status_code == 201
    task = response.json()
    assert task["status"] == "draft"
    assert task["task_type"] == "seo_article"

    events_response = client.get(f"/api/tasks/{task['id']}/events")
    assert events_response.status_code == 200
    events = events_response.json()
    assert len(events) == 1
    assert events[0]["event_type"] == "task_created"
    assert events[0]["to_status"] == "draft"


def test_task_requires_product_or_topic(client):
    response = client.post(
        "/api/tasks",
        json={
            "task_type": "seo_article",
            "language": "ru",
        },
    )

    assert response.status_code == 422


def test_valid_task_transition(client):
    create_response = client.post(
        "/api/tasks",
        json={
            "task_type": "seo_article",
            "language": "ru",
            "topic": "Starlink verification guide",
        },
    )
    task = create_response.json()

    transition_response = client.post(
        f"/api/tasks/{task['id']}/status",
        json={"status": "queued", "current_step": "queued for research"},
    )

    assert transition_response.status_code == 200
    assert transition_response.json()["status"] == "queued"

    events_response = client.get(f"/api/tasks/{task['id']}/events")
    events = events_response.json()
    assert [event["event_type"] for event in events] == ["task_created", "status_changed"]
    assert events[1]["from_status"] == "draft"
    assert events[1]["to_status"] == "queued"


def test_invalid_task_transition(client):
    create_response = client.post(
        "/api/tasks",
        json={
            "task_type": "seo_article",
            "language": "ru",
            "topic": "Starlink verification guide",
        },
    )
    task = create_response.json()

    transition_response = client.post(
        f"/api/tasks/{task['id']}/status",
        json={"status": "done"},
    )

    assert transition_response.status_code == 409


def test_enqueue_task_moves_draft_to_queued(client):
    create_response = client.post(
        "/api/tasks",
        json={
            "task_type": "seo_article",
            "language": "ru",
            "topic": "Starlink verification guide",
        },
    )
    task = create_response.json()

    enqueue_response = client.post(f"/api/tasks/{task['id']}/enqueue")

    assert enqueue_response.status_code == 200
    payload = enqueue_response.json()
    assert payload["task_id"] == task["id"]
    assert payload["queue"] == "fake"
    assert payload["job_id"] == f"fake-{task['id']}"
    assert payload["status"] == "queued"

    events_response = client.get(f"/api/tasks/{task['id']}/events")
    events = events_response.json()
    assert [event["event_type"] for event in events] == ["task_created", "status_changed"]
    assert events[-1]["to_status"] == "queued"
