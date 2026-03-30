from pathlib import Path

import pytest

from deerflow.config.paths import Paths


def test_user_paths_are_built_under_users_directory(tmp_path: Path):
    paths = Paths(base_dir=tmp_path)

    assert paths.user_dir("user-123") == tmp_path / "users" / "user-123"
    assert paths.user_thread_dir("user-123", "thread_456") == tmp_path / "users" / "user-123" / "threads" / "thread_456"
    assert paths.user_thread_tmp_dir("user-123", "thread_456") == tmp_path / "users" / "user-123" / "threads" / "thread_456" / "user-data" / "tmp"
    assert paths.user_skills_dir("user-123") == tmp_path / "users" / "user-123" / "skills" / "custom"


def test_ensure_user_thread_dirs_creates_standard_directories(tmp_path: Path):
    paths = Paths(base_dir=tmp_path)

    paths.ensure_user_thread_dirs("user-123", "thread_456")

    assert paths.user_sandbox_work_dir("user-123", "thread_456").is_dir()
    assert paths.user_sandbox_uploads_dir("user-123", "thread_456").is_dir()
    assert paths.user_sandbox_outputs_dir("user-123", "thread_456").is_dir()
    assert paths.user_thread_tmp_dir("user-123", "thread_456").is_dir()


def test_user_thread_dir_rejects_unsafe_thread_id(tmp_path: Path):
    paths = Paths(base_dir=tmp_path)

    with pytest.raises(ValueError, match="Invalid thread_id"):
        paths.user_thread_dir("user-123", "../bad")
