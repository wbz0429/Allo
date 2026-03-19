"""SQLAlchemy ORM models for multi-tenant organization data."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class Organization(Base):
    """Organization (tenant) model.

    Each organization represents a tenant in the multi-tenant system.
    Better Auth manages user/session tables; we only add org-related tables.
    """

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    members: Mapped[list["OrganizationMember"]] = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Organization(id={self.id!r}, name={self.name!r}, slug={self.slug!r})>"


class OrganizationMember(Base):
    """Organization membership model.

    Links users (managed by Better Auth) to organizations with a role.
    """

    __tablename__ = "organization_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, insert_default="member")

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "role" not in kwargs:
            kwargs["role"] = "member"
        super().__init__(**kwargs)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="members")

    def __repr__(self) -> str:
        return f"<OrganizationMember(id={self.id!r}, org_id={self.org_id!r}, user_id={self.user_id!r}, role={self.role!r})>"


class TenantConfig(Base):
    """Per-tenant configuration overrides.

    Stores JSON config overrides that are merged with the base YAML config
    at runtime. Each organization has at most one config row.

    Attributes:
        id: UUID primary key.
        org_id: Foreign key to organizations.id (unique — one config per org).
        config_json: JSON string of config overrides.
        updated_at: Timestamp of last update.
    """

    __tablename__ = "tenant_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, insert_default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    organization: Mapped["Organization"] = relationship("Organization")

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "config_json" not in kwargs:
            kwargs["config_json"] = "{}"
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<TenantConfig(id={self.id!r}, org_id={self.org_id!r})>"
