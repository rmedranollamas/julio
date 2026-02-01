from skills_loader import SkillsLoader
import os
import shutil

def test_skills():
    loader = SkillsLoader("./skills")
    skills_prompt = loader.load_skills()
    print(f"Skills Prompt:\n{skills_prompt}")
    assert "Test Skill" in skills_prompt

    resources = loader.get_skill_resources("test-skill")
    print(f"Resources: {resources.keys()}")
    assert "resource.txt" in resources
    assert resources["resource.txt"].strip() == "Resource content"

    print("Skills loader test PASSED")

if __name__ == "__main__":
    test_skills()
