import os
from pathlib import Path

from deerflow.config.paths import get_paths


def ensure_runtime_base_dir_is_service_owned(
    base_dir: Path,
    *,
    expected_uid: int | None = None,
    expected_gid: int | None = None,
    stat_result: tuple[int, int] | None = None,
) -> None:
    """Fail fast when the DeerFlow runtime directory is not owned by the service user."""
    uid = os.getuid() if expected_uid is None else expected_uid
    gid = os.getgid() if expected_gid is None else expected_gid

    if stat_result is None:
        stat = base_dir.stat()
        owner_uid, owner_gid = stat.st_uid, stat.st_gid
    else:
        owner_uid, owner_gid = stat_result

    if owner_uid != uid or owner_gid != gid:
        raise RuntimeError(f"Runtime base dir {base_dir} is owned by unexpected user/group ({owner_uid}:{owner_gid}); expected {uid}:{gid}. Fix ownership before starting services.")


def verify_runtime_base_dir_ownership() -> None:
    ensure_runtime_base_dir_is_service_owned(get_paths().base_dir)
