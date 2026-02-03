import pytest
import os
import shutil
import asyncio
from skills_loader import SkillsLoader

@pytest.mark.asyncio
async def test_load_skills(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    skill1 = skills_dir / "skill1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("Skill 1 content")

    skill2 = skills_dir / "skill2"
    skill2.mkdir()
    (skill2 / "SKILL.md").write_text("Skill 2 content")

    # A directory without SKILL.md
    (skills_dir / "not_a_skill").mkdir()

    loader = SkillsLoader(str(skills_dir))
    content = await loader.load_skills()

    assert "## Available Skills" in content
    assert "### Skill: skill1" in content
    assert "Skill 1 content" in content
    assert "### Skill: skill2" in content
    assert "Skill 2 content" in content
    assert "not_a_skill" not in content

@pytest.mark.asyncio
async def test_load_skills_empty(tmp_path):
    skills_dir = tmp_path / "empty_skills"
    skills_dir.mkdir()

    loader = SkillsLoader(str(skills_dir))
    content = await loader.load_skills()
    assert content == ""

@pytest.mark.asyncio
async def test_load_skills_nonexistent():
    loader = SkillsLoader("/nonexistent/path")
    content = await loader.load_skills()
    assert content == ""
