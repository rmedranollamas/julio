import os
import asyncio
from typing import List, Dict

class SkillsLoader:
    def __init__(self, skills_path: str):
        self.skills_path = skills_path

    async def load_skills(self) -> str:
        def _get_skill_paths():
            if not os.path.exists(self.skills_path):
                return []
            paths = []
            try:
                for item in os.listdir(self.skills_path):
                    item_path = os.path.join(self.skills_path, item)
                    if os.path.isdir(item_path):
                        skill_md_path = os.path.join(item_path, "SKILL.md")
                        if os.path.exists(skill_md_path):
                            paths.append((item, skill_md_path))
            except Exception:
                pass
            return paths

        skill_info = await asyncio.to_thread(_get_skill_paths)
        if not skill_info:
            return ""

        def _read_batch(batch):
            results = []
            for item, path in batch:
                try:
                    with open(path, "r") as f:
                        content = f.read()
                        results.append(f"### Skill: {item}\n{content}")
                except Exception:
                    pass
            return results

        # Batching to reduce thread pool overhead
        batch_size = 100
        batches = [skill_info[i:i + batch_size] for i in range(0, len(skill_info), batch_size)]

        tasks = [asyncio.to_thread(_read_batch, batch) for batch in batches]
        batch_results = await asyncio.gather(*tasks)

        skills_content = [item for sublist in batch_results for item in sublist]

        if not skills_content:
            return ""

        return "\n\n".join(["## Available Skills", *skills_content])
