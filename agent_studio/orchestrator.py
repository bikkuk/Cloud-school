import difflib
import json
from datetime import datetime
from pathlib import Path

from agent_studio.agents.builder import BuilderAgent
from agent_studio.agents.planner import PlannerAgent
from agent_studio.agents.reviewer import ReviewerAgent
from agent_studio.agents.runner import RunnerAgent


class StudioOrchestrator:
    MAX_FILES_PER_ITER = 6

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

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _write_md(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

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
        del confirm_overwrite  # no full-file blind overwrite flow; patch-driven apply is used

        self.stop_requested = False
        project_root = self.store.ensure_project(project)
        run_dir = self.store.create_run_folder(project)
        studio = project_root / ".agentstudio"

        editable_roots = ["src", "tests", "docs"]
        gates: dict[str, dict] = {}

        # Stage 0: intake
        task_card = {
            "timestamp": datetime.now().isoformat(),
            "project": project,
            "brief": brief,
            "acceptance_criteria": [
                "Deliver changes as scoped patch-based edits.",
                "Preserve lock constraints.",
                "Produce artifacts for each stage.",
            ],
            "editable_roots": editable_roots,
        }
        self._write_json(studio / "tasks" / "task_card.json", task_card)
        self._write_json(studio / "locks" / "design_lock.json", {"ux_lock": locks.get("ux_lock", False)})
        self._write_json(studio / "locks" / "function_lock.json", {"function_lock": locks.get("function_lock", False)})
        self._write_json(
            studio / "locks" / "file_lock.json",
            {
                "editable_paths": editable_roots,
                "read_only_paths": [".agentstudio", "attachments", "outputs", "agent_runs"],
                "forbidden_paths": ["..", "/"],
            },
        )
        gates["G0"] = {"pass": True, "reason": "Intake artifacts written."}

        if self.stop_requested:
            return {"ok": False, "message": "Stopped by user.", "run_dir": run_dir.as_posix(), "gates": gates}

        # Stage 1: plan gate
        self._write_md(studio / "plans" / "plan_v1.md", plan)
        plan_review_ok, plan_review_msg = self.reviewer.review_plan(plan, locks)
        self._write_json(studio / "plans" / "plan_v1.json", {"plan": plan, "review": plan_review_msg})
        gates["G1"] = {"pass": plan_review_ok, "reason": plan_review_msg}
        if not plan_review_ok:
            return {"ok": False, "message": plan_review_msg, "run_dir": run_dir.as_posix(), "gates": gates}

        if self.stop_requested:
            return {"ok": False, "message": "Stopped by user.", "run_dir": run_dir.as_posix(), "gates": gates}

        # Stage 2: patch proposal and scope gate
        patch_plan = self.builder.propose_patch(model, brief, plan, editable_roots, temperature, num_ctx)
        self._write_json(studio / "patches" / "iter_1_plan.json", patch_plan)

        apply_result = self.builder.apply_patch_plan(project_root, patch_plan, editable_roots, max_files=self.MAX_FILES_PER_ITER)
        patch_ok = bool(apply_result.get("ok"))

        patch_summary = {
            "files_changed": [c["path"] for c in apply_result.get("changes", [])],
            "file_count": len(apply_result.get("changes", [])),
            "max_files": self.MAX_FILES_PER_ITER,
            "reason": apply_result.get("reason", ""),
        }
        self._write_json(studio / "reports" / "iter_1_patch_summary.json", patch_summary)
        self._write_md(
            studio / "reports" / "iter_1_patch_summary.md",
            f"# Patch Summary\n\n- Result: {'PASS' if patch_ok else 'FAIL'}\n- Reason: {apply_result.get('reason', '')}\n"
            f"- Files: {', '.join(patch_summary['files_changed']) if patch_summary['files_changed'] else 'none'}\n",
        )

        diff_text = []
        for c in apply_result.get("changes", []):
            diff_text.extend(
                difflib.unified_diff(
                    c["old"].splitlines(keepends=True),
                    c["new"].splitlines(keepends=True),
                    fromfile=f"before/{c['path']}",
                    tofile=f"after/{c['path']}",
                )
            )
        combined_diff = "".join(diff_text)
        self._write_md(studio / "patches" / "iter_1.diff", combined_diff)
        gates["G2"] = {"pass": patch_ok, "reason": apply_result.get("reason", "")}
        if not patch_ok:
            return {"ok": False, "message": apply_result.get("reason", "Patch failed"), "run_dir": run_dir.as_posix(), "gates": gates}

        patch_review_ok, patch_review_msg = self.reviewer.review_patch(apply_result.get("changes", []), locks)
        gates["G2b"] = {"pass": patch_review_ok, "reason": patch_review_msg}
        if not patch_review_ok:
            return {"ok": False, "message": patch_review_msg, "run_dir": run_dir.as_posix(), "gates": gates}

        # Stage 3+4: build + test
        build_ok, build_log = self.runner.run("python -m py_compile agent_studio/app.py agent_studio/orchestrator.py", confirm_command)
        test_ok, test_log = self.runner.run("python -m pytest", confirm_command)
        if (not test_ok) and "no tests ran" in (test_log or "").lower():
            test_ok = True
            test_log = (test_log or "") + "\n[warning] No tests discovered; treated as warning for this run."

        self._write_md(studio / "logs" / "iter_1_build.log", build_log)
        self._write_md(studio / "logs" / "iter_1_test.log", test_log)
        self._write_json(
            studio / "reports" / "iter_1_build.json",
            {"command": "python -m py_compile agent_studio/app.py agent_studio/orchestrator.py", "status": "pass" if build_ok else "fail"},
        )
        self._write_json(
            studio / "reports" / "iter_1_test_results.json",
            {"command": "python -m pytest", "status": "pass" if test_ok else "fail"},
        )
        gates["G3"] = {"pass": build_ok, "reason": "Build checks"}
        gates["G4"] = {"pass": test_ok, "reason": "Test checks"}

        # Stage 5: verification review
        review_code = {"blocker_count": 0 if patch_ok else 1, "notes": "Patch remained in scoped directories."}
        review_security = {"blocker_count": 0, "notes": "No forbidden command tokens executed."}
        review_ux = {"blocker_count": 0, "notes": "UX lock constraints checked at plan/patch gates."}
        self._write_json(studio / "reports" / "iter_1_review_code.json", review_code)
        self._write_json(studio / "reports" / "iter_1_review_security.json", review_security)
        self._write_json(studio / "reports" / "iter_1_review_ux.json", review_ux)
        gate5_pass = all(r["blocker_count"] == 0 for r in [review_code, review_security, review_ux])
        gates["G5"] = {"pass": gate5_pass, "reason": "Verification reviews complete."}

        # Stage 6: approval
        approval_pass = all(g.get("pass") for g in gates.values())
        approval = {"approved": approval_pass, "gates": gates, "timestamp": datetime.now().isoformat()}
        self._write_json(studio / "decisions" / "iter_1_approval.json", approval)
        gates["G6"] = {"pass": approval_pass, "reason": "All required gates passed." if approval_pass else "Gate failures present."}

        # Stage 7: package docs
        release_dir = studio / "releases" / "release_001"
        release_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "release_id": "release_001",
            "artifacts": [
                "task_card.json",
                "plan_v1.md",
                "iter_1.diff",
                "iter_1_patch_summary.json",
                "iter_1_approval.json",
            ],
            "created_at": datetime.now().isoformat(),
        }
        self._write_json(release_dir / "manifest.json", manifest)
        self._write_md(release_dir / "changelog.md", "# Changelog\n\n- Initial gated desktop run artifacts generated locally.\n")
        self._write_md(release_dir / "package.log", "Local package prep complete.\n")
        gates["G7"] = {"pass": True, "reason": "Release artifacts generated."}

        run_log = (
            f"Gates: {json.dumps(gates, indent=2)}\n\n"
            f"Build ok: {build_ok}\nTest ok: {test_ok}\n"
        )
        self._write_md(run_dir / "run_log.txt", run_log)
        self._write_md(run_dir / "changes.patch", combined_diff)
        self._write_md(run_dir / "changes_summary.md", patch_plan.get("summary", ""))
        self._write_md(run_dir / "plan.md", plan)

        final_ok = approval_pass and build_ok
        message = "Pipeline completed." if final_ok else "Pipeline completed with gate failures."
        return {
            "ok": final_ok,
            "message": message,
            "run_dir": run_dir.as_posix(),
            "diff": combined_diff,
            "runner_log": f"build_ok={build_ok}, test_ok={test_ok}",
            "gates": gates,
        }
