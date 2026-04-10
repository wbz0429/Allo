from pathlib import Path

import pytest

from app.gateway.runtime_paths_guard import ensure_runtime_base_dir_is_service_owned


def test_runtime_base_dir_guard_accepts_service_owned_directory(tmp_path: Path) -> None:
    base_dir = tmp_path / ".deer-flow"
    base_dir.mkdir()

    ensure_runtime_base_dir_is_service_owned(base_dir, expected_uid=1000, expected_gid=1000, stat_result=(1000, 1000))


def test_runtime_base_dir_guard_rejects_foreign_owner(tmp_path: Path) -> None:
    base_dir = tmp_path / ".deer-flow"
    base_dir.mkdir()

    with pytest.raises(RuntimeError, match="owned by unexpected user/group"):
        ensure_runtime_base_dir_is_service_owned(base_dir, expected_uid=1000, expected_gid=1000, stat_result=(1001, 1001))
