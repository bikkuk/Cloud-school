import difflib
from pathlib import Path

from agent_studio.agents.builder import BuilderAgent
from agent_studio.agents.planner import PlannerAgent
from agent_studio.agents.reviewer import ReviewerAgent
from agent_studio.agents.runner import RunnerAgent


class StudioOrchestrator:
    def __init__(self, llm_client, project_store, allowlist_path: str):
        self.planner = PlannerAgent(llm_client)
        self.builder = BuilderAgent(llm_client)
        self.reviewer = ReviewerAgent()
        self.runner = RunnerAgent(allowlist_path)
        self.store = project_store
        self.stop_requested = False

    def stop(self):
        self.stop_requested = True

    def generate_plan(self, project: str, model: str, brief: str, temperature: float, num_ctx: int) -> str:
        self.store.save_brief(project, brief)
        plan = self.planner.build_plan(model, brief, temperature, num_ctx)
        self.store.append_prompt_history(project, {"type": "plan", "model": model, "brief": brief, "plan": plan})
        return plan

    def run(
        self,
        project: str,
        model: str,
        brief: str,
        plan: str,
        temperature: float,
        num_ctx: int,
        locks: dict[str, bool],
        confirm_overwrite,
        confirm_command,
    ) -> dict:
        self.stop_requested = False
        run_dir = self.store.create_run_folder(project)
        outputs_dir = self.store.project_path(project) / "outputs"

        (run_dir / "plan.md").write_text(plan, encoding="utf-8")
        approved, review_msg = self.reviewer.review(plan, locks)
        if not approved:
            (run_dir / "run_log.txt").write_text(review_msg, encoding="utf-8")
            return {"ok": False, "message": review_msg, "run_dir": run_dir.as_posix()}

        if self.stop_requested:
            return {"ok": False, "message": "Stopped by user.", "run_dir": run_dir.as_posix()}

        summary = self.builder.propose_changes(model, brief, plan, temperature, num_ctx)
        (run_dir / "changes_summary.md").write_text(summary, encoding="utf-8")

        output_file = outputs_dir / "generated_output.md"
        old = output_file.read_text(encoding="utf-8") if output_file.exists() else ""
        wrote, write_msg = self.builder.write_output_with_preview(output_file, summary, confirm_overwrite)

        diff_text = ""
        if wrote:
            new = output_file.read_text(encoding="utf-8")
            diff = difflib.unified_diff(
                old.splitlines(keepends=True),
                new.splitlines(keepends=True),
                fromfile="before/generated_output.md",
                tofile="after/generated_output.md",
            )
            diff_text = "".join(diff)
            (run_dir / "changes.patch").write_text(diff_text, encoding="utf-8")

        run_ok, runner_log = self.runner.run("python -m pytest", confirm_command)
        log_text = f"Reviewer: {review_msg}\nBuilder: {write_msg}\nRunner ok={run_ok}\n\n{runner_log}"
        (run_dir / "run_log.txt").write_text(log_text, encoding="utf-8")

        return {
            "ok": wrote,
            "message": write_msg,
            "run_dir": run_dir.as_posix(),
            "diff": diff_text,
            "runner_log": runner_log,
        }
