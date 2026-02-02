import os
from typing import List, Dict

class SkillsLoader:
    def __init__(self, skills_path: str):
        self.skills_path = skills_path

    def load_skills(self) -> str:
        if not os.path.exists(self.skills_path):
            return ""

        skills_content = []
        for item in os.listdir(self.skills_path):
            item_path = os.path.join(self.skills_path, item)
            if os.path.isdir(item_path):
                skill_md_path = os.path.join(item_path, "SKILL.md")
                if os.path.exists(skill_md_path):
                    with open(skill_md_path, "r") as f:
                        content = f.read()
                        skills_content.append(f"### Skill: {item}\n{content}")

        if not skills_content:
            return ""

        return "\n\n".join(["## Available Skills", *skills_content])

    def get_skill_resources(self, skill_name: str) -> Dict[str, str]:
        resources = {}
        skill_path = os.path.join(self.skills_path, skill_name)
        if os.path.isdir(skill_path):
            for root, dirs, files in os.walk(skill_path):
                for file in files:
                    if file != "SKILL.md":
                        rel_path = os.path.relpath(os.path.join(root, file), skill_path)
                        try:
                            with open(os.path.join(root, file), "r") as f:
                                resources[rel_path] = f.read()
                        except:
                            # Skip binary or unreadable files
                            pass
        return resources
