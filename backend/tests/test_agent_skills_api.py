from app.config import Settings, get_settings


def _write_skill(tmp_path):
    skill_dir = tmp_path / "ecommerce-api-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "---",
                "name: ecommerce-api-skill",
                "description: API-visible test skill.",
                "metadata:",
                "  version: 0.2.0",
                "---",
                "",
                "# API Skill",
            ]
        ),
        encoding="utf-8",
    )


def test_sync_and_get_skill_via_api(client, tmp_path):
    _write_skill(tmp_path)
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        skill_registry_root=str(tmp_path)
    )

    sync_response = client.post("/api/skills/sync")

    assert sync_response.status_code == 200
    assert sync_response.json() == {"scanned": 1, "upserted": 1, "archived": 0}

    list_response = client.get("/api/skills")
    skills = list_response.json()

    assert list_response.status_code == 200
    assert len(skills) == 1
    assert skills[0]["name"] == "ecommerce-api-skill"
    assert skills[0]["version"] == "0.2.0"

    get_response = client.get("/api/skills/by-name/ecommerce-api-skill")

    assert get_response.status_code == 200
    assert get_response.json()["description"] == "API-visible test skill."
