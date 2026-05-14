from app.services.skill_registry import list_agent_skills, sync_agent_skills


def _write_skill(tmp_path, slug="ecommerce-test-skill", name="ecommerce-test-skill"):
    skill_dir = tmp_path / slug
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "\n".join(
            [
                "---",
                f"name: {name}",
                "description: Test skill for ecommerce workflow.",
                "metadata:",
                "  version: 0.1.0",
                "---",
                "",
                "# Test Skill",
                "",
                "Use this skill in tests.",
            ]
        ),
        encoding="utf-8",
    )
    return skill_file


def test_sync_agent_skills_is_idempotent(db_session, tmp_path):
    _write_skill(tmp_path)

    first = sync_agent_skills(db_session, tmp_path)
    second = sync_agent_skills(db_session, tmp_path)
    skills = list_agent_skills(db_session)

    assert first.scanned == 1
    assert first.upserted == 1
    assert first.archived == 0
    assert second.scanned == 1
    assert second.upserted == 1
    assert second.archived == 0
    assert len(skills) == 1
    assert skills[0].name == "ecommerce-test-skill"
    assert skills[0].version == "0.1.0"


def test_sync_agent_skills_archives_missing_skill(db_session, tmp_path):
    skill_file = _write_skill(tmp_path)
    sync_agent_skills(db_session, tmp_path)

    skill_file.unlink()
    skill_file.parent.rmdir()
    result = sync_agent_skills(db_session, tmp_path)
    active_skills = list_agent_skills(db_session)
    archived_skills = list_agent_skills(db_session, status="archived")

    assert result.archived == 1
    assert active_skills == []
    assert len(archived_skills) == 1
