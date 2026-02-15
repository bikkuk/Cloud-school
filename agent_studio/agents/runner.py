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
        if self._is_blocked(cmd):
            return False, "Blocked command detected. Refusing to execute."

        if not self._is_allowed(cmd):
            if not confirm_callback(cmd):
                return False, f"User declined non-allowlisted command: {cmd}"

        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, output.strip()
