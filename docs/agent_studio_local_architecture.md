# Agent Studio (Local-First) Architecture Spec

## 1) Full Pipeline (Steps + Pass/Fail Gates)

### Stage 0 — Intake & Constraints Freeze
**Goal:** capture user intent and lock the sandbox before any generation.

**Actions**
1. Parse request into objective, scope, tech stack, and target runtime.
2. Build `task_card.json` with explicit acceptance criteria.
3. Build lock manifests:
   - `design_lock.json` (UI/layout constraints)
   - `function_lock.json` (critical APIs/behavior)
   - `file_lock.json` (non-editable and editable scopes)
4. Select model routing profile (planner/code/fast).

**Artifacts**
- `.agentstudio/tasks/task_card.json`
- `.agentstudio/locks/design_lock.json`
- `.agentstudio/locks/function_lock.json`
- `.agentstudio/locks/file_lock.json`
- `.agentstudio/logs/00_intake.md`

**Gate G0 (Pass/Fail)**
- PASS if acceptance criteria, file scope, and locks are present and valid JSON schema.
- FAIL if any lock is missing or user scope is ambiguous.
- On FAIL: ask user for missing constraints.

---

### Stage 1 — Plan
**Goal:** produce a deterministic implementation plan with bounded file edits.

**Actions**
1. Create stepwise plan with estimated touched files and risks.
2. Enforce max file-change budget (e.g., default 6 files/iteration).
3. Create test plan (unit/integration/e2e/static/security as relevant).

**Artifacts**
- `.agentstudio/plans/plan_v{n}.json`
- `.agentstudio/plans/plan_v{n}.md`

**Gate G1**
- PASS if every planned change maps to allowed file scopes and tests are defined.
- FAIL if plan exceeds file budget or touches locked files.
- On FAIL: auto-replan with smaller increments.

---

### Stage 2 — Patch Proposal
**Goal:** generate scoped patch only (no full-file rewrites unless explicitly allowed).

**Actions**
1. Builder agents emit unified diffs by file.
2. Compute patch summary: files touched, line counts, lock-impact check.
3. Reject any patch that edits out-of-scope paths.

**Artifacts**
- `.agentstudio/patches/iter_{k}.diff`
- `.agentstudio/reports/iter_{k}_patch_summary.json`
- `.agentstudio/reports/iter_{k}_patch_summary.md`

**Gate G2**
- PASS if patch is parseable, in-scope, under file budget, and lock-safe.
- FAIL if patch is destructive, oversized, or out-of-scope.
- On FAIL: send to Fix Planner with explicit violations.

---

### Stage 3 — Apply & Build
**Goal:** apply patch in working tree and perform deterministic build/lint.

**Actions**
1. Apply patch.
2. Run formatter/linter/type checks.
3. Run project build command.

**Artifacts**
- `.agentstudio/logs/iter_{k}_apply.log`
- `.agentstudio/logs/iter_{k}_build.log`
- `.agentstudio/reports/iter_{k}_build.json`

**Gate G3**
- PASS if patch applies cleanly and build/lint/type checks pass.
- FAIL otherwise.
- On FAIL: route to Debug/Fix agent; do not advance.

---

### Stage 4 — Test
**Goal:** verify functionality and prevent regressions.

**Actions**
1. Run targeted tests for changed areas.
2. Run regression suite when existing features exist.
3. Run smoke tests for app startup and key user flow.

**Artifacts**
- `.agentstudio/logs/iter_{k}_test.log`
- `.agentstudio/reports/iter_{k}_test_results.json`
- `.agentstudio/reports/iter_{k}_test_results.md`

**Gate G4**
- PASS if required tests pass and coverage delta is acceptable.
- FAIL on any critical test failure.
- On FAIL: route to Fix agent with failing test traces.

---

### Stage 5 — Verification Review
**Goal:** independent review by QA/security/UX reviewers.

**Actions**
1. Code Review Agent checks maintainability and architecture conformance.
2. Security Agent checks dangerous patterns, secrets, and dependency risks.
3. UX Agent checks UI behavior against design lock (if UI project).

**Artifacts**
- `.agentstudio/reports/iter_{k}_review_code.json|md`
- `.agentstudio/reports/iter_{k}_review_security.json|md`
- `.agentstudio/reports/iter_{k}_review_ux.json|md`

**Gate G5**
- PASS if no blocker-level findings.
- FAIL if blocker findings exist.
- On FAIL: create fix tasks and loop back to Stage 2.

---

### Stage 6 — Approval
**Goal:** explicit quality decision with traceability.

**Actions**
1. Aggregate all gate outcomes.
2. Produce decision packet with checklist and evidence links.
3. If risk score above threshold, require human confirmation.

**Artifacts**
- `.agentstudio/decisions/iter_{k}_approval.json`
- `.agentstudio/decisions/iter_{k}_approval.md`

**Gate G6**
- PASS if all required gates passed and risk is acceptable.
- FAIL otherwise.

---

### Stage 7 — Package & Release Prep
**Goal:** produce release candidate assets locally.

**Actions**
1. Generate changelog and docs updates.
2. Build local package/bundle.
3. Snapshot lockfiles + artifact manifest.

**Artifacts**
- `.agentstudio/releases/release_{r}/manifest.json`
- `.agentstudio/releases/release_{r}/changelog.md`
- `.agentstudio/releases/release_{r}/package.log`

**Gate G7**
- PASS if package builds and docs/manifests are complete.
- FAIL if packaging or documentation is incomplete.

---

## 2) Agent Definitions (14 Total)

### Template fields used below
- **Purpose**
- **Inputs**
- **Outputs**
- **Allowed file scope**
- **Locks respected**
- **Strict output format**

---

## A. Production Agents (Builders)

### 1. Product Planner Agent
- **Purpose:** Convert user request into concrete execution plan and acceptance criteria.
- **Inputs:** `task_card.json`, repository map, lock manifests.
- **Outputs:** `plan_v{n}.json`, `plan_v{n}.md`.
- **Allowed file scope:** `.agentstudio/plans/**`, `.agentstudio/tasks/**`.
- **Locks respected:** must not alter locks; only read them.
- **Strict output format:**
  - JSON: `{plan_id, goals[], steps[{id,desc,files[],tests[]}], risks[], budget{max_files,max_lines}}`
  - MD summary with table of steps/files/tests.

### 2. Architecture Agent
- **Purpose:** Define module boundaries and dependency-safe design updates.
- **Inputs:** plan, existing `src/**`, `docs/**`.
- **Outputs:** `architecture_delta.md`, optional `architecture_delta.json`.
- **Allowed file scope:** `docs/**`, `.agentstudio/reports/**`.
- **Locks respected:** design lock + function lock.
- **Strict output format:** JSON with `proposed_modules`, `interfaces_changed`, `impact_score` + MD rationale.

### 3. Backend Builder Agent
- **Purpose:** Implement server/business logic changes with minimal diffs.
- **Inputs:** plan step, architecture delta, tests baseline.
- **Outputs:** unified diff + `backend_change_report.json|md`.
- **Allowed file scope:** `src/**`, `project/**` backend folders only as whitelisted.
- **Locks respected:** function lock, file lock.
- **Strict output format:**
  - Diff file.
  - JSON: `{files_changed[], funcs_added[], funcs_modified[], lock_violations:[]}`

### 4. Frontend/UI Builder Agent
- **Purpose:** Implement UI updates without breaking locked layouts/components.
- **Inputs:** design lock, style guide, UI tests.
- **Outputs:** unified diff + `ui_change_report.json|md`.
- **Allowed file scope:** UI directories only (`src/ui/**`, `src/components/**`, styles).
- **Locks respected:** design lock, file lock.
- **Strict output format:** JSON with `components_touched`, `visual_risks`, `a11y_expectations` + MD preview notes.

### 5. Data/Schema Agent
- **Purpose:** Handle database schema/migration/model changes safely.
- **Inputs:** plan step, existing schema, migration history.
- **Outputs:** migration diff + `schema_impact.json|md`.
- **Allowed file scope:** `src/data/**`, `migrations/**`, schema files.
- **Locks respected:** function lock on public API behavior.
- **Strict output format:** JSON with `migration_id`, `forward_steps`, `rollback_steps`, `compatibility`.

### 6. Integration Agent
- **Purpose:** Wire modules/APIs; ensure interfaces match across layers.
- **Inputs:** backend/frontend diffs, architecture interfaces.
- **Outputs:** integration patch + `integration_report.json|md`.
- **Allowed file scope:** only integration files declared in plan.
- **Locks respected:** function lock + file lock.
- **Strict output format:** JSON with `contracts_verified`, `adapters_changed`, `breaking_change=false/true`.

---

## B. Verification Agents (QA/Review/Security/UX)

### 7. Test Generator Agent
- **Purpose:** Add/update targeted tests for modified behavior.
- **Inputs:** patch summary, acceptance criteria.
- **Outputs:** test diffs + `test_plan_exec.json|md`.
- **Allowed file scope:** `tests/**` only.
- **Locks respected:** file lock.
- **Strict output format:** JSON with `tests_added`, `tests_updated`, `traceability[{criterion,test_id}]`.

### 8. Build & Lint Agent
- **Purpose:** Execute formatter/lint/type/build checks and normalize logs.
- **Inputs:** repo state, command policy.
- **Outputs:** `build.json|md`, raw logs.
- **Allowed file scope:** `.agentstudio/logs/**`, `.agentstudio/reports/**`.
- **Locks respected:** no source edits permitted.
- **Strict output format:** JSON with `commands[]`, `exit_codes[]`, `duration_s`, `status`.

### 9. Functional Test Runner Agent
- **Purpose:** Run unit/integration/e2e suites and regression packs.
- **Inputs:** test plan, baseline results.
- **Outputs:** `test_results.json|md`, failure traces.
- **Allowed file scope:** `.agentstudio/logs/**`, `.agentstudio/reports/**`.
- **Locks respected:** no source edits.
- **Strict output format:** JSON with `pass_count`, `fail_count`, `flaky_suspects[]`, `regression_status`.

### 10. Code Review Agent
- **Purpose:** Static review for code quality, complexity, and architecture drift.
- **Inputs:** patch, architecture docs, coding standards.
- **Outputs:** `review_code.json|md`.
- **Allowed file scope:** `.agentstudio/reports/**`.
- **Locks respected:** no source edits.
- **Strict output format:** JSON with findings `[{severity,file,line,issue,fix_hint}]` and `blocker_count`.

### 11. Security Review Agent
- **Purpose:** Detect secrets, insecure APIs, unsafe command usage, dependency vulnerabilities.
- **Inputs:** diff, dependency manifest, command logs.
- **Outputs:** `review_security.json|md`.
- **Allowed file scope:** `.agentstudio/reports/**`, `.agentstudio/logs/**`.
- **Locks respected:** no source edits.
- **Strict output format:** JSON with `cwe_findings[]`, `secret_scan`, `dependency_risk`, `blocker_count`.

### 12. UX & Accessibility Review Agent
- **Purpose:** Validate UX flows, consistency, accessibility basics.
- **Inputs:** UI diff, design lock, screenshot/test outputs.
- **Outputs:** `review_ux.json|md`.
- **Allowed file scope:** `.agentstudio/reports/**`.
- **Locks respected:** design lock.
- **Strict output format:** JSON with `ux_findings[]`, `a11y_checks[]`, `blocker_count`.

---

## C. Release Agents (Packaging/Docs)

### 13. Documentation Agent
- **Purpose:** Update README, usage notes, architecture notes, and change summaries.
- **Inputs:** approved patch, decision packet.
- **Outputs:** docs diffs + `docs_update_report.json|md`.
- **Allowed file scope:** `docs/**`, `README*`, `.agentstudio/releases/**`.
- **Locks respected:** file lock.
- **Strict output format:** JSON with `docs_changed[]`, `user_visible_changes[]`, `upgrade_notes`.

### 14. Packager Agent
- **Purpose:** Build local release artifacts and manifest.
- **Inputs:** approved code state, packaging config.
- **Outputs:** build artifacts + `manifest.json`, `package.log`, `release_notes.md`.
- **Allowed file scope:** `.agentstudio/releases/**`, `dist/**` (or configured output dir only).
- **Locks respected:** no source edits unless explicitly approved.
- **Strict output format:** JSON manifest with checksums and artifact paths.

---

## Lock System (applies to all agents)

### Design Lock
- Freezes screen hierarchy, component IDs/classes, and critical UX flows.
- UI agents may only adjust regions marked mutable in lock config.

### Function Lock
- Freezes public function signatures, endpoint contracts, and side-effect guarantees.
- Any required function-lock change triggers mandatory user approval before patch stage.

### File Lock
- Explicit whitelist/blacklist:
  - `editable_paths[]`
  - `read_only_paths[]`
  - `forbidden_paths[]`
- Orchestrator validates every diff hunk path before apply.

---

## 3) Control Loop Spec (Plan → Patch → Test → Review → Fix → Retest → Approve → Package)

```python
MAX_ITERATIONS = 8
MAX_FILES_PER_ITER = 6
MAX_BLOCKER_RETRIES = 3

state = load_or_init_state()

for iteration in range(1, MAX_ITERATIONS + 1):
    write_log(f"iteration {iteration} start")

    # PLAN
    plan = planner_agent.run(state)
    gate_g1 = validate_plan(plan, locks=state.locks, file_budget=MAX_FILES_PER_ITER)
    save_artifacts(plan, gate_g1)
    if not gate_g1.pass_:
        if gate_g1.reason == "ambiguous_scope":
            request_user_input(gate_g1.questions)
            break
        state = replan(state, gate_g1.violations)
        continue

    # PATCH
    diff = builder_swarm.run(plan, locks=state.locks)
    patch_check = validate_patch(diff, locks=state.locks, max_files=MAX_FILES_PER_ITER)
    save_artifacts(diff, patch_check)
    if not patch_check.pass_:
        state = create_fix_tasks("patch_violations", patch_check.violations)
        continue

    apply_result = apply_diff(diff)
    if not apply_result.pass_:
        state = create_fix_tasks("apply_failure", apply_result.errors)
        continue

    # TEST
    build_result = build_lint_agent.run()
    test_result = test_runner_agent.run(regression_required=state.has_existing_features)
    save_artifacts(build_result, test_result)
    if not (build_result.pass_ and test_result.pass_):
        state = create_fix_tasks("test_failures", collect_failures(build_result, test_result))
        continue

    # REVIEW
    code_review = code_review_agent.run(diff)
    sec_review = security_review_agent.run(diff)
    ux_review = ux_review_agent.run_if_ui_changed(diff)
    blockers = count_blockers(code_review, sec_review, ux_review)
    save_artifacts(code_review, sec_review, ux_review)

    if blockers > 0:
        state.blocker_retries += 1
        if state.blocker_retries >= MAX_BLOCKER_RETRIES:
            request_user_input({
                "reason": "persistent_blockers",
                "details": summarize_blockers(code_review, sec_review, ux_review)
            })
            break
        state = create_fix_tasks("review_blockers", merge_findings(code_review, sec_review, ux_review))
        continue

    # APPROVE
    approval = make_approval_decision(plan, build_result, test_result, code_review, sec_review, ux_review)
    save_artifacts(approval)
    if not approval.pass_:
        request_user_input({"reason": "approval_denied", "details": approval.details})
        break

    # PACKAGE
    package_result = packager_agent.run()
    docs_result = documentation_agent.run()
    save_artifacts(package_result, docs_result)

    if package_result.pass_ and docs_result.pass_:
        mark_done()
        break
    else:
        state = create_fix_tasks("release_failures", collect_failures(package_result, docs_result))

if not state.done:
    write_log("terminated without completion")
```

### Stop / Ask-User Conditions
1. Scope ambiguity persists after one replan.
2. Function lock must change.
3. Blocker findings persist beyond retry cap.
4. Iteration cap reached.
5. Command policy requires confirmation for dangerous ops.

---

## 4) Minimal Folder Structure Template

```text
/project
  /.agentstudio
    /tasks
      task_card.json
    /plans
      plan_v1.json
      plan_v1.md
    /locks
      design_lock.json
      function_lock.json
      file_lock.json
    /patches
      iter_1.diff
    /reports
      iter_1_patch_summary.json
      iter_1_test_results.json
      iter_1_review_code.json
      iter_1_review_security.json
      iter_1_review_ux.json
    /logs
      iter_1_apply.log
      iter_1_build.log
      iter_1_test.log
    /decisions
      iter_1_approval.json
    /releases
      /release_001
        manifest.json
        changelog.md
        package.log
  /src
  /tests
  /docs
```

---

## 5) Model Routing Recommendation (Ollama local)

### Planner model (higher reasoning)
Use for:
- Requirement decomposition
- Architecture decisions
- Test strategy generation
- Review synthesis and approval decisions

### Code model (strong code diff behavior)
Use for:
- Patch generation
- Refactoring within strict file scope
- Test implementation
- Bug fixes from failure traces

### Fast chat model (low latency)
Use for:
- Log summarization
- Status updates
- Minor report drafting
- Non-critical reformatting

### Routing Rules
1. Always run planning/review on planner model.
2. Always run code changes on code model.
3. Use fast model for meta tasks only; never final quality gates.
4. If planner/code disagree, planner decides task intent; code model regenerates patch.

---

## 6) Command Execution Policy

### Auto-allowed commands (no confirmation)
- Read-only ops: directory listing, file reads, metadata.
- Safe dev checks: formatter, lint, unit tests, type checks, local build.
- Local packaging commands that write only to `dist/` or `.agentstudio/releases/`.

### Confirmation-required commands
- Deleting files outside temp/build directories.
- Global dependency upgrades or lockfile regeneration that affects many modules.
- DB destructive migrations (drop/truncate) or irreversible transforms.
- Git history rewriting (`reset --hard`, force push).
- Any command touching paths outside project root.

### Log Safety
- Capture stdout/stderr separately and combined.
- Redact secrets (tokens/keys/password-like patterns) before persistence.
- Store command, cwd, timestamp, exit code, duration, redaction flags in JSON.

---

## 7) Safe Iteration Policy (Anti-destructive)

1. **Patch summary mandatory** before apply:
   - files changed, line delta, lock check results.
2. **File change cap per iteration** (default `N=6`):
   - if patch exceeds cap, split automatically or request approval.
3. **Strict path enforcement:**
   - reject diffs for non-whitelisted paths.
4. **No full project rewrites:**
   - prefer hunk-level edits; full-file replacement only with explicit approval.
5. **Regression checks mandatory** when pre-existing features exist.
6. **Rollback-ready:**
   - every applied patch stored as `.diff` and reversible.
7. **Deterministic retries:**
   - each retry must reference prior failure IDs and produce narrower patch.
8. **Human escalation triggers:**
   - repeated blockers, lock conflicts, or risky commands.

---

## 8) Windows 10/11 Local Implementation Notes

- Orchestrator: Python CLI/service (no Electron required).
- Runtime: Ollama local model endpoint (`http://localhost:<port>` default local service).
- Use Windows-native process execution with timeout + kill tree for stuck commands.
- Keep project-local virtual environments and toolchains to avoid global drift.
- Use JSON schema validation for all agent outputs before progressing gates.
