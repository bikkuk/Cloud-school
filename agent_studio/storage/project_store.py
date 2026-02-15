import json
import shutil
from datetime import datetime
from pathlib import Path


class ProjectStore:
    def __init__(self, root: str = "studio_projects"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> list[str]:
        return sorted([p.name for p in self.root.iterdir() if p.is_dir()])

    def project_path(self, project_name: str) -> Path:
        return self.root / project_name

    def ensure_project(self, project_name: str) -> Path:
        path = self.project_path(project_name)
        (path / "agent_runs").mkdir(parents=True, exist_ok=True)
        (path / "outputs").mkdir(parents=True, exist_ok=True)
        (path / "attachments").mkdir(parents=True, exist_ok=True)

        for file_name in ["project_brief.md", "plan.md", "run_log.txt", "changes.patch"]:
            file_path = path / file_name
            if not file_path.exists():
                file_path.write_text("", encoding="utf-8")

        history_file = path / "prompt_history.jsonl"
        history_file.touch(exist_ok=True)
        return path

    def save_brief(self, project_name: str, brief_text: str) -> None:
        project = self.ensure_project(project_name)
        (project / "project_brief.md").write_text(brief_text, encoding="utf-8")

    def load_brief(self, project_name: str) -> str:
        project = self.ensure_project(project_name)
        return (project / "project_brief.md").read_text(encoding="utf-8")

    def save_plan(self, project_name: str, plan_text: str) -> None:
        project = self.ensure_project(project_name)
        (project / "plan.md").write_text(plan_text, encoding="utf-8")

    def append_run_log(self, project_name: str, log_text: str) -> None:
        project = self.ensure_project(project_name)
        (project / "run_log.txt").write_text(log_text, encoding="utf-8")

    def save_changes_patch(self, project_name: str, patch_text: str) -> None:
        project = self.ensure_project(project_name)
        (project / "changes.patch").write_text(patch_text, encoding="utf-8")

    def append_prompt_history(self, project_name: str, payload: dict) -> None:
        project = self.ensure_project(project_name)
        line = json.dumps(payload, ensure_ascii=False)
        with (project / "prompt_history.jsonl").open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def create_run_folder(self, project_name: str) -> Path:
        project = self.ensure_project(project_name)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = project / "agent_runs" / stamp
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def copy_attachment(self, project_name: str, source_path: str) -> Path:
        project = self.ensure_project(project_name)
        src = Path(source_path)
        dest = project / "attachments" / src.name
        shutil.copy2(src, dest)
        return dest
