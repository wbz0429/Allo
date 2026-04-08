import builtins
import os

import deerflow.sandbox.local.local_sandbox as local_sandbox
from deerflow.sandbox.local.local_sandbox import LocalSandbox


def _open(base, file, mode="r", *args, **kwargs):
    if "b" in mode:
        return base(file, mode, *args, **kwargs)
    return base(file, mode, *args, encoding=kwargs.pop("encoding", "gbk"), **kwargs)


def test_read_file_uses_utf8_on_windows_locale(tmp_path, monkeypatch):
    path = tmp_path / "utf8.txt"
    text = "\u201cutf8\u201d"
    path.write_text(text, encoding="utf-8")
    base = builtins.open

    monkeypatch.setattr(local_sandbox, "open", lambda file, mode="r", *args, **kwargs: _open(base, file, mode, *args, **kwargs), raising=False)

    assert LocalSandbox("t").read_file(str(path)) == text


def test_write_file_uses_utf8_on_windows_locale(tmp_path, monkeypatch):
    path = tmp_path / "utf8.txt"
    text = "emoji \U0001f600"
    base = builtins.open

    monkeypatch.setattr(local_sandbox, "open", lambda file, mode="r", *args, **kwargs: _open(base, file, mode, *args, **kwargs), raising=False)

    LocalSandbox("t").write_file(str(path), text)

    assert path.read_text(encoding="utf-8") == text


# ---------- Sandbox environment isolation ----------


def test_build_sandbox_env_removes_venv_from_path(monkeypatch):
    """_build_sandbox_env should strip .venv entries from PATH."""
    monkeypatch.setenv("PATH", "/usr/local/bin:/srv/allo/backend/.venv/bin:/usr/bin:/bin")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    env = LocalSandbox._build_sandbox_env()

    path_dirs = env["PATH"].split(os.pathsep)
    assert not any(".venv" in d for d in path_dirs)
    assert "/usr/local/bin" in path_dirs
    assert "/usr/bin" in path_dirs
    assert "/bin" in path_dirs


def test_build_sandbox_env_removes_virtual_env(monkeypatch):
    """_build_sandbox_env should remove VIRTUAL_ENV variable."""
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.setenv("VIRTUAL_ENV", "/srv/allo/backend/.venv")

    env = LocalSandbox._build_sandbox_env()

    assert "VIRTUAL_ENV" not in env


def test_build_sandbox_env_sets_pip_mirror(monkeypatch):
    """_build_sandbox_env should set pip mirror defaults."""
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.delenv("PIP_INDEX_URL", raising=False)
    monkeypatch.delenv("PIP_TRUSTED_HOST", raising=False)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    env = LocalSandbox._build_sandbox_env()

    assert "tuna.tsinghua" in env["PIP_INDEX_URL"]
    assert "tuna.tsinghua" in env["PIP_TRUSTED_HOST"]


def test_build_sandbox_env_does_not_override_existing_pip_mirror(monkeypatch):
    """If PIP_INDEX_URL is already set, _build_sandbox_env should not override it."""
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.setenv("PIP_INDEX_URL", "https://custom-mirror.example.com/simple/")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    env = LocalSandbox._build_sandbox_env()

    assert env["PIP_INDEX_URL"] == "https://custom-mirror.example.com/simple/"


def test_build_sandbox_env_handles_mac_venv_path(monkeypatch):
    """macOS-style .venv paths should also be stripped."""
    monkeypatch.setenv("PATH", "/opt/homebrew/bin:/Users/steven/VaaT-Flow/backend/.venv/bin:/usr/local/bin:/usr/bin:/bin")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    env = LocalSandbox._build_sandbox_env()

    path_dirs = env["PATH"].split(os.pathsep)
    assert not any(".venv" in d for d in path_dirs)
    assert "/opt/homebrew/bin" in path_dirs
