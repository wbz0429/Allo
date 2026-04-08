import os
import shutil
import subprocess

from deerflow.sandbox.local.list_dir import list_dir
from deerflow.sandbox.sandbox import Sandbox


class LocalSandbox(Sandbox):
    def __init__(self, id: str):
        """
        Initialize local sandbox.

        Args:
            id: Sandbox identifier
        """
        super().__init__(id)
        self._sandbox_env: dict[str, str] | None = None

    @staticmethod
    def _build_sandbox_env() -> dict[str, str]:
        """Build a clean environment for sandbox subprocess execution.

        Removes service-process virtualenv paths from PATH to prevent
        the agent from discovering and using the host's .venv.
        Also injects pip mirror configuration for reliable package installation.
        """
        env = os.environ.copy()

        # Remove .venv entries from PATH to isolate agent from service Python
        path_dirs = env.get("PATH", "").split(os.pathsep)
        clean_path = os.pathsep.join(d for d in path_dirs if ".venv" not in d)
        env["PATH"] = clean_path

        # Remove VIRTUAL_ENV to prevent python from thinking it's in a venv
        env.pop("VIRTUAL_ENV", None)

        # Set pip mirror for reliable package installation (China mainland)
        env.setdefault("PIP_INDEX_URL", "https://pypi.tuna.tsinghua.edu.cn/simple/")
        env.setdefault("PIP_TRUSTED_HOST", "pypi.tuna.tsinghua.edu.cn")

        return env

    def _get_sandbox_env(self) -> dict[str, str]:
        """Get or create the cached sandbox environment."""
        if self._sandbox_env is None:
            self._sandbox_env = self._build_sandbox_env()
        return self._sandbox_env

    @staticmethod
    def _get_shell() -> str:
        """Detect available shell executable with fallback.

        Returns the first available shell in order of preference:
        /bin/zsh → /bin/bash → /bin/sh → first `sh` found on PATH.
        Raises a RuntimeError if no suitable shell is found.
        """
        for shell in ("/bin/zsh", "/bin/bash", "/bin/sh"):
            if os.path.isfile(shell) and os.access(shell, os.X_OK):
                return shell
        shell_from_path = shutil.which("sh")
        if shell_from_path is not None:
            return shell_from_path
        raise RuntimeError("No suitable shell executable found. Tried /bin/zsh, /bin/bash, /bin/sh, and `sh` on PATH.")

    def execute_command(self, command: str) -> str:
        result = subprocess.run(
            command,
            executable=self._get_shell(),
            shell=True,
            capture_output=True,
            text=True,
            timeout=600,
            env=self._get_sandbox_env(),
        )
        output = result.stdout
        if result.stderr:
            output += f"\nStd Error:\n{result.stderr}" if output else result.stderr
        if result.returncode != 0:
            output += f"\nExit Code: {result.returncode}"

        return output if output else "(no output)"

    def list_dir(self, path: str, max_depth=2) -> list[str]:
        return list_dir(path, max_depth)

    def read_file(self, path: str) -> str:
        with open(path, encoding="utf-8") as f:
            return f.read()

    def write_file(self, path: str, content: str, append: bool = False) -> None:
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        mode = "a" if append else "w"
        with open(path, mode, encoding="utf-8") as f:
            f.write(content)

    def update_file(self, path: str, content: bytes) -> None:
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
