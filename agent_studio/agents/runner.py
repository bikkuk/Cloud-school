import json
import subprocess
from pathlib import Path


class RunnerAgent:
    def __init__(self, allowlist_path: str):
        config = json.loads(Path(allowlist_path).read_text(encoding="utf-8"))
        self.allowed = config.get("allowed_commands", [])
        self.blocked_tokens = [t.lower() for t in config.get("blocked_tokens", [])]

    def _is_blocked(self, cmd: str) -> bool:
        lcmd = f" {cmd.lower()} "
        return any(token in lcmd for token in self.blocked_tokens)

    def _is_allowed(self, cmd: str) -> bool:
        if cmd.strip() == "python -m pytest" and Path("tests").exists():
            return True
        if cmd.strip().startswith("python ") and cmd.strip().endswith(".py"):
            return True
        return cmd in self.allowed

    def run(self, cmd: str, confirm_callback) -> tuple[bool, str]:
        action_log = [f"Requested command: {cmd}"]

        if self._is_blocked(cmd):
            action_log.append("Blocked command detected. Refusing to execute.")
            return False, "\n".join(action_log)

        if not self._is_allowed(cmd):
            action_log.append("Command not allowlisted. Asking user for explicit confirmation.")
            if not confirm_callback(cmd):
                action_log.append("User declined execution.")
                return False, "\n".join(action_log)
            action_log.append("User approved execution.")

        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        action_log.append(f"Return code: {proc.returncode}")
        if proc.stdout:
            action_log.append("[stdout]")
            action_log.append(proc.stdout.strip())
        if proc.stderr:
            action_log.append("[stderr]")
            action_log.append(proc.stderr.strip())
        return proc.returncode == 0, "\n".join(action_log).strip()
