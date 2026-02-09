import os
import asyncio
import threading
from typing import Dict, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class SkillChangeHandler(FileSystemEventHandler):
    def __init__(self, loader: "SkillsLoader"):
        self.loader = loader

    def on_any_event(self, event):
        self.loader.clear_cache(event.src_path)


class SkillsLoader:
    def __init__(self, skills_path: str):
        self.skills_path = os.path.abspath(skills_path)
        self._cache_load_skills: Optional[str] = None
        self._cache_resources: Dict[str, Dict[str, str]] = {}
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()

        self.observer = Observer()
        self.event_handler = SkillChangeHandler(self)
        self._observer_started = False
        self._ensure_observer_started()

    def _ensure_observer_started(self):
        with self._lock:
            if not self._observer_started and os.path.exists(self.skills_path):
                try:
                    self.observer.schedule(
                        self.event_handler, self.skills_path, recursive=True
                    )
                    self.observer.start()
                    self._observer_started = True
                except OSError:
                    # Could fail if directory is deleted right after check
                    pass

    def clear_cache(self, changed_path: Optional[str] = None):
        with self._lock:
            self._cache_load_skills = None
            if changed_path is None:
                self._cache_resources = {}
            else:
                try:
                    rel_path = os.path.relpath(changed_path, self.skills_path)
                    skill_name = rel_path.split(os.sep)[0]
                    if skill_name in self._cache_resources:
                        del self._cache_resources[skill_name]
                except ValueError:
                    # path not under skills_path
                    self._cache_resources = {}

    def stop(self):
        with self._lock:
            if self._observer_started:
                self.observer.stop()
                self.observer.join()
                self._observer_started = False

    async def load_skills(self) -> str:
        # Fast-path check without acquiring the async lock
        with self._lock:
            if self._cache_load_skills is not None:
                return self._cache_load_skills

        async with self._async_lock:
            # Re-check after acquiring the lock to handle concurrent reloads
            with self._lock:
                if self._cache_load_skills is not None:
                    return self._cache_load_skills

            def _get_skill_paths():
                if not os.path.exists(self.skills_path):
                    return []
                paths = []
                try:
                    with os.scandir(self.skills_path) as it:
                        for entry in it:
                            if entry.is_dir():
                                skill_md_path = os.path.join(entry.path, "SKILL.md")
                                if os.path.exists(skill_md_path):
                                    paths.append((entry.name, skill_md_path))
                except OSError:
                    pass
                return paths

            skill_info = await asyncio.to_thread(_get_skill_paths)
            if not skill_info:
                return ""

            # Check granular cache
            skills_to_read = []
            with self._lock:
                for name, path in skill_info:
                    if (
                        name not in self._cache_resources
                        or "SKILL.md" not in self._cache_resources[name]
                    ):
                        skills_to_read.append((name, path))

            if skills_to_read:

                def _read_batch(batch):
                    results = []
                    for name, path in batch:
                        try:
                            with open(path, "r") as f:
                                content = f.read()
                                results.append((name, content))
                        except OSError:
                            pass
                    return results

                # Batching to reduce thread pool overhead
                batch_size = 100
                batches = [
                    skills_to_read[i : i + batch_size]
                    for i in range(0, len(skills_to_read), batch_size)
                ]

                tasks = [asyncio.to_thread(_read_batch, batch) for batch in batches]
                batch_results = await asyncio.gather(*tasks)

                newly_read = [item for sublist in batch_results for item in sublist]
                with self._lock:
                    for name, content in newly_read:
                        if name not in self._cache_resources:
                            self._cache_resources[name] = {}
                        self._cache_resources[name]["SKILL.md"] = content

            # Reconstruct from cache in original order
            skills_content = []
            with self._lock:
                for name, _ in skill_info:
                    if (
                        name in self._cache_resources
                        and "SKILL.md" in self._cache_resources[name]
                    ):
                        content = self._cache_resources[name]["SKILL.md"]
                        skills_content.append(f"### Skill: {name}\n{content}")

            result = "\n\n".join(["## Available Skills", *skills_content])
            with self._lock:
                self._cache_load_skills = result
            return result
