"""Tests for skill upload endpoint."""

import io
import shutil
import zipfile

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.gateway.routers.skills import router, _get_user_custom_skills_dir

# Minimal app for testing
app = FastAPI()
app.include_router(router)

TEST_USER_ID = "test-upload-user-001"


def _make_skill_zip(
    name: str = "test-skill",
    description: str = "A test skill",
    extra_files: dict[str, str] | None = None,
    extra_frontmatter: dict[str, str | bool | int] | None = None,
) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        frontmatter_lines = ["---", f"name: {name}", f"description: {description}"]
        if extra_frontmatter:
            for key, value in extra_frontmatter.items():
                rendered = str(value).lower() if isinstance(value, bool) else value
                frontmatter_lines.append(f"{key}: {rendered}")
        frontmatter_lines.extend(["---", "", f"# {name}"])
        frontmatter = "\n".join(frontmatter_lines) + "\n"
        zf.writestr(f"{name}/SKILL.md", frontmatter)
        if extra_files:
            for path, content in extra_files.items():
                zf.writestr(f"{name}/{path}", content)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _mock_auth():
    from app.gateway.auth import get_auth_context

    class FakeAuth:
        user_id = TEST_USER_ID
        org_id = "test-org"
        role = "admin"

    app.dependency_overrides[get_auth_context] = lambda: FakeAuth()
    yield
    app.dependency_overrides.pop(get_auth_context, None)


@pytest.fixture(autouse=True)
def _clean():
    custom_dir = _get_user_custom_skills_dir(TEST_USER_ID)
    if custom_dir.exists():
        shutil.rmtree(custom_dir)
    yield
    if custom_dir.exists():
        shutil.rmtree(custom_dir)


@pytest.mark.asyncio
async def test_upload_valid_skill():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/skills/upload", files={"file": ("s.zip", _make_skill_zip("upload-ok"), "application/zip")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["skill_name"] == "upload-ok"
    assert (_get_user_custom_skills_dir(TEST_USER_ID) / "upload-ok" / "SKILL.md").exists()


@pytest.mark.asyncio
async def test_upload_skill_allows_user_invocable_frontmatter():
    data = _make_skill_zip("user-invocable-skill", extra_frontmatter={"user_invocable": True})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/skills/upload", files={"file": ("s.zip", data, "application/zip")})

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["skill_name"] == "user-invocable-skill"


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_value", ["maybe", 1])
async def test_upload_skill_rejects_invalid_user_invocable_value(invalid_value: str | int):
    data = _make_skill_zip("bad-user-invocable", extra_frontmatter={"user_invocable": invalid_value})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/skills/upload", files={"file": ("s.zip", data, "application/zip")})

    assert resp.status_code == 400
    assert "user_invocable" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_upload_with_companion_files():
    data = _make_skill_zip("rich", "Rich skill", {"scripts/run.py": "print(1)", "refs/guide.md": "# G"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/skills/upload", files={"file": ("r.zip", data, "application/zip")})
    assert resp.status_code == 200
    d = _get_user_custom_skills_dir(TEST_USER_ID) / "rich"
    assert (d / "scripts" / "run.py").exists()
    assert (d / "refs" / "guide.md").exists()


@pytest.mark.asyncio
async def test_upload_duplicate_returns_409():
    data = _make_skill_zip("dup")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r1 = await c.post("/api/skills/upload", files={"file": ("d.zip", data, "application/zip")})
        assert r1.status_code == 200
        r2 = await c.post("/api/skills/upload", files={"file": ("d.zip", data, "application/zip")})
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_upload_bad_extension():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/skills/upload", files={"file": ("bad.txt", b"x", "text/plain")})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_no_skill_md():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "no skill")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/skills/upload", files={"file": ("b.zip", buf.getvalue(), "application/zip")})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_not_a_zip():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/skills/upload", files={"file": ("f.zip", b"not zip", "application/zip")})
    assert resp.status_code == 400
