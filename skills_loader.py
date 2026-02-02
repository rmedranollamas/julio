import os
import threading
from typing import List, Dict, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class SkillChangeHandler(FileSystemEventHandler):
    def __init__(self, loader: 'SkillsLoader'):
        self.loader = loader

    def on_any_event(self, event):
        if not event.is_directory:
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

    def load_skills(self) -> str:
        self._ensure_observer_started()
        with self._lock:
            if self._cache_load_skills is not None:
                return self._cache_load_skills

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
            result = ""
        else:
            result = "\n\n".join(["## Available Skills", *skills_content])

        with self._lock:
            self._cache_load_skills = result
        return result

    def get_skill_resources(self, skill_name: str) -> Dict[str, str]:
        self._ensure_observer_started()
        with self._lock:
            if skill_name in self._cache_resources:
                return self._cache_resources[skill_name]

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

        with self._lock:
            self._cache_resources[skill_name] = resources
        return resources
