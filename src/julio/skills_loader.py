import os
import asyncio
import threading
from typing import List, Dict, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class SkillChangeHandler(FileSystemEventHandler):
    def __init__(self, loader: 'SkillsLoader'):
        self.loader = loader

    def on_any_event(self, event):
        self.loader.clear_cache(event.src_path)

class SkillsLoader:
    def __init__(self, skills_path: str):
        self.skills_path = os.path.abspath(skills_path)
        self._cache_load_skills: Optional[str] = None
        self._cache_resources: Dict[str, Dict[str, str]] = {}
        self._lock = threading.Lock()

        self.observer = Observer()
        self.event_handler = SkillChangeHandler(self)
        self._observer_started = False
        self._ensure_observer_started()

    def _ensure_observer_started(self):
        with self._lock:
            if not self._observer_started and os.path.exists(self.skills_path):
                try:
                    self.observer.schedule(self.event_handler, self.skills_path, recursive=True)
                    self.observer.start()
                    self._observer_started = True
                except Exception:
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
            result = ""
        else:
            result = "\n\n".join(["## Available Skills", *skills_content])

        return "\n\n".join(["## Available Skills", *skills_content])
