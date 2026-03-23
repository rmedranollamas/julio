import asyncio
import time
import os
import shutil
import tempfile
import gc
from julio.skills_loader import SkillsLoader

async def benchmark():
    tmp_dir = tempfile.mkdtemp()
    skills_dir = os.path.join(tmp_dir, "skills")
    os.mkdir(skills_dir)

    num_skills = 2000
    for i in range(num_skills):
        skill_dir = os.path.join(skills_dir, f"skill_{i}")
        os.mkdir(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write(f"Content for skill {i} " * 50)

    loader = SkillsLoader(skills_dir)

    # Warm up
    await loader.load_skills()

    num_runs = 5
    times = []

    for _ in range(num_runs):
        loader.clear_cache()
        gc.collect()

        start_time = time.perf_counter()
        await loader.load_skills()
        end_time = time.perf_counter()
        times.append(end_time - start_time)

    avg_time = sum(times) / num_runs
    print(f"Average time to load {num_skills} skills over {num_runs} runs: {avg_time:.4f} seconds")

    loader.stop()
    shutil.rmtree(tmp_dir)

if __name__ == "__main__":
    asyncio.run(benchmark())
