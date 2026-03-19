"""Tests for the database models: Organization and OrganizationMember."""

import uuid
from datetime import datetime, timezone

from app.gateway.db.models import Base, Organization, OrganizationMember


# ---------------------------------------------------------------------------
# Organization model tests
# ---------------------------------------------------------------------------


def test_organization_creation() -> None:
    org = Organization(id="org-1", name="Acme Corp", slug="acme-corp")
    assert org.id == "org-1"
    assert org.name == "Acme Corp"
    assert org.slug == "acme-corp"


def test_organization_default_id() -> None:
    org = Organization(name="Test Org", slug="test-org")
    # Default factory should produce a valid UUID string
    assert org.id is not None
    uuid.UUID(org.id)  # Raises if not valid UUID


def test_organization_repr() -> None:
    org = Organization(id="org-1", name="Acme", slug="acme")
    r = repr(org)
    assert "Organization" in r
    assert "org-1" in r
    assert "Acme" in r
    assert "acme" in r


def test_organization_tablename() -> None:
    assert Organization.__tablename__ == "organizations"


def test_organization_columns() -> None:
    col_names = {c.name for c in Organization.__table__.columns}
    assert col_names == {"id", "name", "slug", "created_at", "updated_at"}


def test_organization_slug_unique_constraint() -> None:
    slug_col = Organization.__table__.columns["slug"]
    assert slug_col.unique is True


# ---------------------------------------------------------------------------
# OrganizationMember model tests
# ---------------------------------------------------------------------------


def test_organization_member_creation() -> None:
    member = OrganizationMember(id="m-1", org_id="org-1", user_id="user-1", role="admin")
    assert member.id == "m-1"
    assert member.org_id == "org-1"
    assert member.user_id == "user-1"
    assert member.role == "admin"


def test_organization_member_default_role() -> None:
    member = OrganizationMember(org_id="org-1", user_id="user-1")
    assert member.role == "member"


def test_organization_member_default_id() -> None:
    member = OrganizationMember(org_id="org-1", user_id="user-1")
    assert member.id is not None
    uuid.UUID(member.id)


def test_organization_member_repr() -> None:
    member = OrganizationMember(id="m-1", org_id="org-1", user_id="user-1", role="admin")
    r = repr(member)
    assert "OrganizationMember" in r
    assert "m-1" in r
    assert "org-1" in r
    assert "user-1" in r
    assert "admin" in r


def test_organization_member_tablename() -> None:
    assert OrganizationMember.__tablename__ == "organization_members"


def test_organization_member_columns() -> None:
    col_names = {c.name for c in OrganizationMember.__table__.columns}
    assert col_names == {"id", "org_id", "user_id", "role", "created_at"}


def test_organization_member_foreign_key() -> None:
    org_id_col = OrganizationMember.__table__.columns["org_id"]
    fk_targets = [fk.target_fullname for fk in org_id_col.foreign_keys]
    assert "organizations.id" in fk_targets


def test_organization_member_user_id_indexed() -> None:
    user_id_col = OrganizationMember.__table__.columns["user_id"]
    assert user_id_col.index is True


# ---------------------------------------------------------------------------
# Base / metadata tests
# ---------------------------------------------------------------------------


def test_base_metadata_contains_both_tables() -> None:
    table_names = set(Base.metadata.tables.keys())
    assert "organizations" in table_names
    assert "organization_members" in table_names


# ---------------------------------------------------------------------------
# Relationship tests (ORM-level, no DB needed)
# ---------------------------------------------------------------------------


def test_organization_has_members_relationship() -> None:
    # Verify the relationship attribute exists on the mapper
    mapper = Organization.__mapper__
    assert "members" in mapper.relationships


def test_organization_member_has_organization_relationship() -> None:
    mapper = OrganizationMember.__mapper__
    assert "organization" in mapper.relationships


def test_cascade_delete_orphan_on_members() -> None:
    rel = Organization.__mapper__.relationships["members"]
    assert "delete" in rel.cascade
    assert "delete-orphan" in rel.cascade
