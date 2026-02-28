class ReviewerAgent:
    def review_plan(self, plan: str, locks: dict[str, bool]) -> tuple[bool, str]:
        violations = []
        lplan = plan.lower()
        if locks.get("function_lock") and any(k in lplan for k in ["signature", "api contract", "breaking change"]):
            violations.append("Function lock is ON and plan suggests API/signature changes.")
        if locks.get("page_lock") and any(k in lplan for k in ["index.html", "web/", "page layout"]):
            violations.append("Page lock is ON and plan suggests page edits.")
        if locks.get("ux_lock") and any(k in lplan for k in ["ui", "component", "layout", "style"]):
            violations.append("UX lock is ON and plan suggests UI changes.")

        if violations:
            return False, "\n".join(violations)
        return True, "Plan review passed: no lock violations detected."

    def review_patch(self, changes: list[dict], locks: dict[str, bool]) -> tuple[bool, str]:
        if locks.get("page_lock"):
            locked_pages = [c["path"] for c in changes if c["path"].startswith("web/") or c["path"] == "index.html"]
            if locked_pages:
                return False, f"Page lock violation: {', '.join(locked_pages)}"
        if locks.get("ux_lock"):
            ux_files = [c["path"] for c in changes if any(seg in c["path"] for seg in ["ui", "component", "style", "css"])]
            if ux_files:
                return False, f"UX lock violation: {', '.join(ux_files)}"
        return True, "Patch review passed."
