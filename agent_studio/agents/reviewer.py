class ReviewerAgent:
    def review(self, plan: str, locks: dict[str, bool]) -> tuple[bool, str]:
        violations = []
        if locks.get("function_lock") and "core behavior" in plan.lower():
            violations.append("Function lock is ON and plan appears to modify core behavior.")
        if locks.get("page_lock") and "web" in plan.lower():
            violations.append("Page lock is ON and plan appears to touch web assets.")
        if locks.get("ux_lock") and "ui" in plan.lower():
            violations.append("UX lock is ON and plan appears to alter UI.")

        if violations:
            return False, "\n".join(violations)
        return True, "Review passed: no lock violations detected."
