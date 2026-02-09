import pytest
import asyncio
import os
import shutil
import time
from julio.skills_loader import SkillsLoader

@pytest.mark.asyncio
async def test_skills_loader_cache_invalidation(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    skill1_dir = skills_dir / "skill1"
    skill1_dir.mkdir()
    (skill1_dir / "SKILL.md").write_text("Skill 1 content")

    loader = SkillsLoader(str(skills_dir))

    # Initial load
    content = await loader.load_skills()
    assert "Skill 1 content" in content

    # Add new skill
    skill2_dir = skills_dir / "skill2"
    skill2_dir.mkdir()
    (skill2_dir / "SKILL.md").write_text("Skill 2 content")

    # Watchdog might take a tiny bit to trigger
    # We can try multiple times or just wait
    for _ in range(10):
        await asyncio.sleep(0.1)
        content = await loader.load_skills()
        if "Skill 2 content" in content:
            break

    assert "Skill 2 content" in content

    # Modify skill
    (skill1_dir / "SKILL.md").write_text("Skill 1 updated")
    for _ in range(10):
        await asyncio.sleep(0.1)
        content = await loader.load_skills()
        if "Skill 1 updated" in content:
            break
    assert "Skill 1 updated" in content

    loader.stop()

@pytest.mark.asyncio
async def test_skills_loader_concurrency(tmp_path):
    skills_dir = tmp_path / "skills_concurrent"
    skills_dir.mkdir()
    (skills_dir / "s1").mkdir()
    (skills_dir / "s1" / "SKILL.md").write_text("content")

    loader = SkillsLoader(str(skills_dir))

    # Call load_skills many times concurrently
    results = await asyncio.gather(*(loader.load_skills() for _ in range(10)))

    for r in results:
        assert "content" in r
        assert r == results[0]

    loader.stop()

@pytest.mark.asyncio
async def test_skills_loader_empty(tmp_path):
    loader = SkillsLoader(str(tmp_path / "empty"))
    content = await loader.load_skills()
    assert content == ""
    loader.stop()
