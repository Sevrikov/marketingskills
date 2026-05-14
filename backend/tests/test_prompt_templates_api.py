def _prompt_payload(key="ecommerce.test.v1", version="1.0.0", status="active"):
    return {
        "key": key,
        "name": "Test Prompt",
        "version": version,
        "task_type": "test",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "system_prompt": "You are a test prompt.",
        "user_template": "Process this: {input}",
        "expected_output": "A test output.",
        "validation_schema": {"type": "object"},
        "status": status,
    }


def test_create_and_get_prompt(client):
    create_response = client.post("/api/prompts", json=_prompt_payload())

    assert create_response.status_code == 201
    prompt = create_response.json()
    assert prompt["key"] == "ecommerce.test.v1"

    get_response = client.get(f"/api/prompts/{prompt['id']}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == prompt["id"]


def test_get_active_prompt_by_key(client):
    client.post("/api/prompts", json=_prompt_payload())

    response = client.get("/api/prompts/by-key/ecommerce.test.v1")

    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_duplicate_prompt_key_version_is_rejected(client):
    payload = _prompt_payload()
    first = client.post("/api/prompts", json=payload)
    second = client.post("/api/prompts", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


def test_deprecated_prompt_is_not_returned_as_active(client):
    client.post("/api/prompts", json=_prompt_payload(status="deprecated"))

    response = client.get("/api/prompts/by-key/ecommerce.test.v1")

    assert response.status_code == 404
