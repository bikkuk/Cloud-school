import difflib
import json
from datetime import datetime
from pathlib import Path

from agent_studio.agents.builder import BuilderAgent
from agent_studio.agents.planner import PlannerAgent
from agent_studio.agents.runner import RunnerAgent
from agent_studio.config.defaults import DEFAULT_ALLOWLIST
from agent_studio.storage.project_store import ProjectStore


class StudioOrchestrator:
    def __init__(self, llm, store: ProjectStore | None = None):
        self.llm = llm
        self.store = store or ProjectStore()
        self._stop = False

        self.planner = PlannerAgent(llm=self.llm)
        self.builder = BuilderAgent(llm=self.llm)
        self.runner = RunnerAgent(llm=self.llm)

    def stop(self):
        self._stop = True

    def generate_plan(self, project: str, brief: str) -> str:
        self._stop = False
        plan = self.planner.generate_plan(project=project, brief=brief)
        self.store.save_plan(project, plan)
        return plan

    def run(
        self,
        project: str,
        plan: str,
        *,
        confirm_overwrite,
        confirm_command,
        log,
        allowlist=None,
    ):
        self._stop = False
        allowlist = allowlist or DEFAULT_ALLOWLIST

        project_dir = self.store.project_path(project)
        project_dir.mkdir(parents=True, exist_ok=True)

        run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        run_dir = project_dir / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        def _log(msg: str):
            try:
                log(msg)
            except Exception:
                pass

        def _read_text(p: Path) -> str:
            if not p.exists():
                return ""
            return p.read_text(encoding="utf-8", errors="ignore")

        def _write_text(p: Path, s: str):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(s, encoding="utf-8")

        def _snapshot_tree(root: Path) -> dict[str, str]:
            snapshot = {}
            for f in root.rglob("*"):
                if f.is_file():
                    # skip run artifacts to avoid diff noise
                    if "runs" in f.parts:
                        continue
                    rel = f.relative_to(root).as_posix()
                    snapshot[rel] = _read_text(f)
            return snapshot

        def _diff_snap(before: dict[str, str], after: dict[str, str]) -> str:
            paths = sorted(set(before.keys()) | set(after.keys()))
            out = []
            for rel in paths:
                a = before.get(rel, "").splitlines(keepends=True)
                b = after.get(rel, "").splitlines(keepends=True)
                if a == b:
                    continue
                out.append(f"--- a/{rel}\n+++ b/{rel}\n")
                out.extend(difflib.unified_diff(a, b, fromfile=f"a/{rel}", tofile=f"b/{rel}"))
                if out and not out[-1].endswith("\n"):
                    out[-1] += "\n"
            return "".join(out)

        # --- Run plan parsing ---
        _log("Parsing plan...")
        patch_plan = self.builder.parse_plan(plan)

        # --- Build (write/modify files) ---
        _log("Applying build steps...")
        before = _snapshot_tree(project_dir)
        writes = self.builder.apply_plan(
            project_dir=project_dir,
            plan=patch_plan,
            confirm_overwrite=confirm_overwrite,
            log=_log,
            stop_flag=lambda: self._stop,
        )
        after = _snapshot_tree(project_dir)
        combined_diff = _diff_snap(before, after)

        # --- Gates / approvals ---
        gates = {}

        # Gate: diff must exist if writes happened
        build_ok = True
        if not writes:
            build_ok = False
            gates["G1"] = {"pass": False, "reason": "No files were written/changed."}
        else:
            gates["G1"] = {"pass": True, "reason": "Files were written/changed."}

        # Gate: command allowlist approval
        approval_pass = True

        # Run commands (including tests)
        _log("Running commands...")
        runner_out = self.runner.run_project(
            project_dir=project_dir,
            plan=patch_plan,
            allowlist=allowlist,
            confirm_command=confirm_command,
            log=_log,
            stop_flag=lambda: self._stop,
        )

        # runner_out should include test_ok; if not, default conservatively to False
        test_ok = bool(runner_out.get("test_ok", False))
        cmd_ok = bool(runner_out.get("ok", False))

        if not cmd_ok:
            approval_pass = False
            gates["G2"] = {"pass": False, "reason": "One or more commands failed or were blocked."}
        else:
            gates["G2"] = {"pass": True, "reason": "Commands executed successfully."}

        if not test_ok:
            gates["G3"] = {"pass": False, "reason": "Tests failed."}
        else:
            gates["G3"] = {"pass": True, "reason": "Tests passed."}

        # Optional: additional gates from runner
        extra_gates = runner_out.get("gates") or {}
        for k, v in extra_gates.items():
            gates[k] = v

        # Write run artifacts
        _write_text(run_dir / "run_log.txt", runner_out.get("log", ""))
        _write_text(run_dir / "changes.patch", combined_diff)
        _write_text(run_dir / "changes_summary.md", patch_plan.get("summary", ""))
        _write_text(run_dir / "plan.md", plan)

        # --- FINAL RESULT (FIXED) ---
        # Must fail if tests fail.
        final_ok = approval_pass and build_ok and test_ok

        if final_ok:
            message = "Pipeline completed."
        else:
            # make the failure reason obvious in the UI
            if not build_ok:
                message = "Pipeline failed: build checks failed."
            elif not test_ok:
                message = "Pipeline failed: tests failed."
            else:
                message = "Pipeline completed with gate failures."

        return {
            "ok": final_ok,
            "message": message,
            "run_dir": run_dir.as_posix(),
            "diff": combined_diff,
            "runner_log": f"build_ok={build_ok}, test_ok={test_ok}",
            "gates": gates,
        }


def load_allowlist(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        return DEFAULT_ALLOWLIST
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_ALLOWLIST