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
        log_path = project / "run_log.txt"
        with log_path.open("a", encoding="utf-8") as f:
            if log_path.stat().st_size > 0:
                f.write("\n\n")
            f.write(log_text)

    def save_changes_patch(self, project_name: str, patch_text: str) -> None:
        project = self.ensure_project(project_name)
        (project / "changes.patch").write_text(patch_text, encoding="utf-8")

    def append_prompt_history(self, project_name: str, payload: dict) -> None:
        project = self.ensure_project(project_name)
        line = json.dumps(payload, ensure_ascii=False)
        with (project / "prompt_history.jsonl").open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def load_prompt_history(self, project_name: str, limit: int = 6) -> list[dict]:
        project = self.ensure_project(project_name)
        path = project / "prompt_history.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines()
        recent = lines[-limit:] if limit > 0 else []
        out = []
        for line in recent:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def get_recent_run_summaries(self, project_name: str, limit: int = 3) -> list[str]:
        project = self.ensure_project(project_name)
        run_root = project / "agent_runs"
        run_dirs = sorted([p for p in run_root.iterdir() if p.is_dir()], reverse=True)[:limit]
        summaries = []
        for run_dir in run_dirs:
            change_file = run_dir / "changes_summary.md"
            log_file = run_dir / "run_log.txt"
            change_text = change_file.read_text(encoding="utf-8")[:500] if change_file.exists() else ""
            log_text = log_file.read_text(encoding="utf-8")[:500] if log_file.exists() else ""
            summaries.append(f"Run {run_dir.name}:\nSummary: {change_text}\nLog: {log_text}")
        return summaries

    def get_outputs_snapshot(self, project_name: str, max_files: int = 5, max_chars: int = 1500) -> str:
        project = self.ensure_project(project_name)
        outputs_dir = project / "outputs"
        files = sorted([p for p in outputs_dir.rglob("*") if p.is_file()])[:max_files]
        chunks = []
        for f in files:
            rel = f.relative_to(outputs_dir).as_posix()
            text = f.read_text(encoding="utf-8", errors="ignore")[:max_chars]
            chunks.append(f"File: {rel}\n{text}")
        return "\n\n".join(chunks)

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
