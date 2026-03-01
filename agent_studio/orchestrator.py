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

    def _memory_context(self, project: str, memory_depth: int) -> str:
        history = self.store.load_prompt_history(project, limit=max(2, memory_depth * 2))
        runs = self.store.get_recent_run_summaries(project, limit=memory_depth)
        outputs = self.store.get_outputs_snapshot(project)

        history_lines = []
        for item in history:
            itype = item.get("type", "unknown")
            model = item.get("model", "")
            brief = str(item.get("brief", ""))[:240]
            history_lines.append(f"type={itype} model={model} brief={brief}")

        parts = []
        if history_lines:
            parts.append("Recent prompt history:\n" + "\n".join(history_lines))
        if runs:
            parts.append("Recent runs:\n" + "\n\n".join(runs))
        if outputs:
            parts.append("Current outputs snapshot:\n" + outputs)
        return "\n\n".join(parts)

    def generate_plan(
        self,
        project: str,
        model: str,
        brief: str,
        temperature: float,
        num_ctx: int,
        use_memory: bool = True,
        memory_depth: int = 3,
    ) -> str:
        self.store.save_brief(project, brief)
        context_notes = self._memory_context(project, memory_depth) if use_memory else ""
        plan = self.planner.build_plan(model, brief, temperature, num_ctx, context_notes=context_notes)
        self.store.save_plan(project, plan)
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
        use_memory: bool = True,
        memory_depth: int = 3,
    ) -> dict:
        self.stop_requested = False
        run_dir = self.store.create_run_folder(project)
        outputs_dir = self.store.project_path(project) / "outputs"

        self.store.save_plan(project, plan)
        (run_dir / "plan.md").write_text(plan, encoding="utf-8")

        approved, review_msg = self.reviewer.review(plan, locks)
        if not approved:
            self.store.append_run_log(project, review_msg)
            (run_dir / "run_log.txt").write_text(review_msg, encoding="utf-8")
            return {"ok": False, "message": review_msg, "run_dir": run_dir.as_posix()}

        if self.stop_requested:
            stop_msg = "Stopped by user."
            self.store.append_run_log(project, stop_msg)
            return {"ok": False, "message": stop_msg, "run_dir": run_dir.as_posix()}

        context_notes = self._memory_context(project, memory_depth) if use_memory else ""
        build_result = self.builder.propose_product_files(
            model=model,
            brief=brief,
            plan=plan,
            temperature=temperature,
            num_ctx=num_ctx,
            context_notes=context_notes,
        )
        summary = str(build_result.get("summary", ""))
        files = build_result.get("files", [])
        (run_dir / "changes_summary.md").write_text(summary or "No summary.", encoding="utf-8")

        writes, write_messages = self.builder.write_files_with_preview(outputs_dir, files, confirm_overwrite)

        diff_chunks = []
        for w in writes:
            diff = difflib.unified_diff(
                w["old"].splitlines(keepends=True),
                w["new"].splitlines(keepends=True),
                fromfile=f"before/{w['path']}",
                tofile=f"after/{w['path']}",
            )
            diff_chunks.append("".join(diff))

        diff_text = "\n".join(diff_chunks).strip()
        if diff_text:
            self.store.save_changes_patch(project, diff_text)
            (run_dir / "changes.patch").write_text(diff_text, encoding="utf-8")

        tests_exist = Path("tests").exists()
        if tests_exist:
            run_ok, runner_log = self.runner.run("python -m pytest", confirm_command)
        else:
            run_ok, runner_log = True, "No tests directory found. Runner skipped command execution."

        write_msg = " ".join(write_messages) if write_messages else "No files written."
        log_text = (
            f"Reviewer: {review_msg}\n"
            f"Builder summary: {summary}\n"
            f"Builder writes: {write_msg}\n"
            f"Runner ok={run_ok}\n\n{runner_log}"
        )
        self.store.append_run_log(project, log_text)
        (run_dir / "run_log.txt").write_text(log_text, encoding="utf-8")

        self.store.append_prompt_history(
            project,
            {
                "type": "run",
                "model": model,
                "brief": brief,
                "plan": plan,
                "summary": summary,
                "written_files": [w["path"] for w in writes],
            },
        )

        return {
            "ok": bool(writes),
            "message": write_msg,
            "run_dir": run_dir.as_posix(),
            "diff": diff_text,
            "runner_log": runner_log,
            "written_files": [w["path"] for w in writes],
        }
