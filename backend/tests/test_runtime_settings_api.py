from app.services.runtime_settings import effective_settings


def test_runtime_settings_masks_secrets_and_updates_models(client, db_session):
    response = client.get("/api/runtime-settings")

    assert response.status_code == 200
    payload = response.json()
    assert "Secrets" in payload["sections"]
    fields = {field["key"]: field for field in payload["fields"]}
    assert fields["google_api_key"]["value"] is None
    assert fields["gemini_content_model"]["value"] == "gemini-2.5-flash-lite"

    update = client.put(
        "/api/runtime-settings",
        json={
            "values": {
                "google_api_key": "test-secret-google-key",
                "llm_provider": "gemini",
                "gemini_content_model": "gemini-3-flash-preview",
                "notification_provider": "viber",
                "viber_auth_token": "test-viber-token",
                "viber_reviewer_ids": "reviewer-1,reviewer-2",
                "enable_real_image_generation": True,
            }
        },
    )

    assert update.status_code == 200
    updated_fields = {field["key"]: field for field in update.json()["fields"]}
    assert updated_fields["google_api_key"]["value"] is None
    assert updated_fields["google_api_key"]["masked_value"].startswith("test")
    assert updated_fields["viber_auth_token"]["masked_value"].endswith("oken")
    assert updated_fields["llm_provider"]["value"] == "gemini"
    assert updated_fields["enable_real_image_generation"]["value"] is True

    settings = effective_settings(db_session)
    assert settings.google_api_key == "test-secret-google-key"
    assert settings.llm_provider == "gemini"
    assert settings.gemini_content_model == "gemini-3-flash-preview"
    assert settings.notification_provider == "viber"
    assert settings.viber_auth_token == "test-viber-token"
    assert settings.viber_reviewer_ids == "reviewer-1,reviewer-2"
    assert settings.enable_real_image_generation is True


def test_runtime_settings_empty_secret_does_not_clear_existing_value(client, db_session):
    client.put(
        "/api/runtime-settings",
        json={"values": {"google_api_key": "persist-me"}},
    )

    response = client.put(
        "/api/runtime-settings",
        json={"values": {"google_api_key": ""}},
    )

    assert response.status_code == 200
    assert effective_settings(db_session).google_api_key == "persist-me"
