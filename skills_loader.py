import os
import asyncio
from typing import List, Dict, Optional

class SkillsLoader:
    def __init__(self, skills_path: str):
        self.skills_path = skills_path

    async def load_skills(self) -> str:
        if not await asyncio.to_thread(os.path.exists, self.skills_path):
            return ""

        items = await asyncio.to_thread(os.listdir, self.skills_path)

        def _load_chunk_sync(chunk_items: List[str]) -> List[str]:
            results = []
            for item in chunk_items:
                item_path = os.path.join(self.skills_path, item)
                if os.path.isdir(item_path):
                    skill_md_path = os.path.join(item_path, "SKILL.md")
                    if os.path.exists(skill_md_path):
                        with open(skill_md_path, "r") as f:
                            content = f.read()
                        results.append(f"### Skill: {item}\n{content}")
            return results

        # Chunk items to reduce thread overhead while maintaining responsiveness
        chunk_size = 1000
        chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

        tasks = [asyncio.to_thread(_load_chunk_sync, chunk) for chunk in chunks]
        results_chunks = await asyncio.gather(*tasks)
        skills_content = [item for chunk in results_chunks for item in chunk]

        if not skills_content:
            return ""

        return "\n\n".join(["## Available Skills", *skills_content])
