"""SQLAlchemy ORM models for multi-tenant organization data."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
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


class User(Base):
    """Application user model for gateway-managed authentication."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, insert_default="zh-CN")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="user", cascade="all, delete-orphan")

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "locale" not in kwargs:
            kwargs["locale"] = "zh-CN"
        if "is_active" not in kwargs:
            kwargs["is_active"] = True
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<User(id={self.id!r}, email={self.email!r})>"


class Session(Base):
    """Persistent login session for cookie-based gateway auth."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="sessions")

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Session(id={self.id!r}, user_id={self.user_id!r})>"


class OrganizationMember(Base):
    """Organization membership model.

    Links users (managed by Better Auth) to organizations with a role.
    """

    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("org_id", "user_id", name="uq_org_user"),)

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


class KnowledgeBase(Base):
    """Knowledge base for RAG document storage and retrieval.

    Each knowledge base belongs to an organization and holds documents
    that are chunked and embedded for semantic search.
    """

    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, insert_default="")
    chunk_size: Mapped[int] = mapped_column(Integer, nullable=False, insert_default=500)
    chunk_overlap: Mapped[int] = mapped_column(Integer, nullable=False, insert_default=50)
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False, insert_default="text-embedding-3-small")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    organization: Mapped["Organization"] = relationship("Organization")
    documents: Mapped[list["KnowledgeDocument"]] = relationship("KnowledgeDocument", back_populates="knowledge_base", cascade="all, delete-orphan")

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "description" not in kwargs:
            kwargs["description"] = ""
        if "chunk_size" not in kwargs:
            kwargs["chunk_size"] = 500
        if "chunk_overlap" not in kwargs:
            kwargs["chunk_overlap"] = 50
        if "embedding_model" not in kwargs:
            kwargs["embedding_model"] = "text-embedding-3-small"
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<KnowledgeBase(id={self.id!r}, name={self.name!r}, org_id={self.org_id!r})>"


class KnowledgeDocument(Base):
    """A document uploaded to a knowledge base.

    Stores the original filename, converted markdown content, and processing status.
    """

    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    kb_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False, insert_default="")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, insert_default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, insert_default="processing")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase", back_populates="documents")
    chunks: Mapped[list["KnowledgeChunk"]] = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "content_md" not in kwargs:
            kwargs["content_md"] = ""
        if "chunk_count" not in kwargs:
            kwargs["chunk_count"] = 0
        if "status" not in kwargs:
            kwargs["status"] = "processing"
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<KnowledgeDocument(id={self.id!r}, filename={self.filename!r}, status={self.status!r})>"


class KnowledgeChunk(Base):
    """A text chunk from a knowledge document with its embedding vector.

    Embeddings are stored as JSON text (list of floats) for simplicity.
    Cosine similarity search is performed in Python.
    """

    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    doc_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    kb_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[str] = mapped_column(Text, nullable=False, insert_default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, insert_default="{}")

    document: Mapped["KnowledgeDocument"] = relationship("KnowledgeDocument", back_populates="chunks")

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "embedding" not in kwargs:
            kwargs["embedding"] = "[]"
        if "metadata_json" not in kwargs:
            kwargs["metadata_json"] = "{}"
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<KnowledgeChunk(id={self.id!r}, doc_id={self.doc_id!r}, chunk_index={self.chunk_index!r})>"


class UsageRecord(Base):
    """Usage tracking record for API calls, LLM tokens, sandbox time, and storage.

    Each record captures one usage event tied to an organization and user.

    Attributes:
        id: UUID primary key.
        org_id: Foreign key to organizations.id.
        user_id: The user who triggered the usage.
        record_type: One of "llm_token", "api_call", "sandbox_time", "storage".
        model_name: LLM model name (nullable, for llm_token type).
        input_tokens: Input token count (for llm_token type).
        output_tokens: Output token count (for llm_token type).
        endpoint: API endpoint path (for api_call type).
        duration_seconds: Duration in seconds (for sandbox_time type).
        created_at: Timestamp of the usage event.
    """

    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    record_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, insert_default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, insert_default=0)
    endpoint: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, insert_default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization: Mapped["Organization"] = relationship("Organization")

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "input_tokens" not in kwargs:
            kwargs["input_tokens"] = 0
        if "output_tokens" not in kwargs:
            kwargs["output_tokens"] = 0
        if "duration_seconds" not in kwargs:
            kwargs["duration_seconds"] = 0.0
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<UsageRecord(id={self.id!r}, org_id={self.org_id!r}, record_type={self.record_type!r})>"


class Thread(Base):
    """Conversation thread metadata owned by a single user."""

    __tablename__ = "threads"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, insert_default="active")
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    runs: Mapped[list["ThreadRun"]] = relationship("ThreadRun", back_populates="thread", cascade="all, delete-orphan")

    def __init__(self, **kwargs: object) -> None:
        if "status" not in kwargs:
            kwargs["status"] = "active"
        super().__init__(**kwargs)


class ThreadRun(Base):
    """Execution run metadata for a thread request."""

    __tablename__ = "thread_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    thread_id: Mapped[str] = mapped_column(String(255), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sandbox_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, insert_default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    thread: Mapped["Thread"] = relationship("Thread", back_populates="runs")

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "status" not in kwargs:
            kwargs["status"] = "running"
        super().__init__(**kwargs)


class UserMemory(Base):
    """Per-user memory document stored in Postgres."""

    __tablename__ = "user_memory"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    context_json: Mapped[str] = mapped_column(Text, nullable=False, insert_default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    facts: Mapped[list["UserMemoryFact"]] = relationship("UserMemoryFact", back_populates="memory", cascade="all, delete-orphan")

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "context_json" not in kwargs:
            kwargs["context_json"] = "{}"
        super().__init__(**kwargs)


class UserMemoryFact(Base):
    """Extracted fact row associated with a user's memory document."""

    __tablename__ = "user_memory_facts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    memory_id: Mapped[str] = mapped_column(String(36), ForeignKey("user_memory.id", ondelete="CASCADE"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, insert_default="context")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, insert_default=0.5)
    source: Mapped[str] = mapped_column(String(100), nullable=False, insert_default="unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    memory: Mapped["UserMemory"] = relationship("UserMemory", back_populates="facts")

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "category" not in kwargs:
            kwargs["category"] = "context"
        if "confidence" not in kwargs:
            kwargs["confidence"] = 0.5
        if "source" not in kwargs:
            kwargs["source"] = "unknown"
        super().__init__(**kwargs)


class UserSoul(Base):
    """Per-user soul/personality content."""

    __tablename__ = "user_souls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, insert_default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "content" not in kwargs:
            kwargs["content"] = ""
        super().__init__(**kwargs)


class UserMcpConfig(Base):
    """Per-user MCP server configuration JSON."""

    __tablename__ = "user_mcp_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, insert_default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "config_json" not in kwargs:
            kwargs["config_json"] = "{}"
        super().__init__(**kwargs)


class UserAgent(Base):
    """Per-user custom agent configuration persisted in Postgres."""

    __tablename__ = "user_agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, insert_default="")
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_groups_json: Mapped[str] = mapped_column(Text, nullable=False, insert_default="[]")
    soul_content: Mapped[str] = mapped_column(Text, nullable=False, insert_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "description" not in kwargs:
            kwargs["description"] = ""
        if "tool_groups_json" not in kwargs:
            kwargs["tool_groups_json"] = "[]"
        if "soul_content" not in kwargs:
            kwargs["soul_content"] = ""
        super().__init__(**kwargs)


class UserApiKey(Base):
    """Encrypted per-user API key configuration."""

    __tablename__ = "user_api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    api_key_enc: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "is_active" not in kwargs:
            kwargs["is_active"] = True
        super().__init__(**kwargs)


# ---------------------------------------------------------------------------
# Marketplace models
# ---------------------------------------------------------------------------


class MarketplaceTool(Base):
    """A tool available in the MCP tool marketplace.

    Stores the tool's metadata and MCP server configuration template.
    Tools can be public (visible to all orgs) or private.

    Attributes:
        id: UUID primary key.
        name: Display name of the tool.
        description: Human-readable description.
        category: One of "search", "code", "data", "communication".
        icon: Icon identifier or URL.
        mcp_config_json: MCP server config template (JSON string).
        is_public: Whether the tool is visible in the public catalog.
        created_at: Timestamp of creation.
    """

    __tablename__ = "marketplace_tools"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, insert_default="")
    category: Mapped[str] = mapped_column(String(50), nullable=False, insert_default="search")
    icon: Mapped[str] = mapped_column(String(512), nullable=False, insert_default="")
    mcp_config_json: Mapped[str] = mapped_column(Text, nullable=False, insert_default="{}")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "description" not in kwargs:
            kwargs["description"] = ""
        if "category" not in kwargs:
            kwargs["category"] = "search"
        if "icon" not in kwargs:
            kwargs["icon"] = ""
        if "mcp_config_json" not in kwargs:
            kwargs["mcp_config_json"] = "{}"
        if "is_public" not in kwargs:
            kwargs["is_public"] = True
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<MarketplaceTool(id={self.id!r}, name={self.name!r}, category={self.category!r})>"


class OrgInstalledTool(Base):
    """Tracks which marketplace tools an organization has installed.

    Stores org-specific configuration (e.g. API keys) for each installed tool.

    Attributes:
        id: UUID primary key.
        org_id: Foreign key to organizations.id.
        tool_id: Foreign key to marketplace_tools.id.
        config_json: Org-specific config overrides (API keys, etc).
        installed_at: Timestamp of installation.
    """

    __tablename__ = "org_installed_tools"
    __table_args__ = (UniqueConstraint("org_id", "tool_id", name="uq_org_tool"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_id: Mapped[str] = mapped_column(String(36), ForeignKey("marketplace_tools.id", ondelete="CASCADE"), nullable=False, index=True)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, insert_default="{}")
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization: Mapped["Organization"] = relationship("Organization")
    tool: Mapped["MarketplaceTool"] = relationship("MarketplaceTool")

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "config_json" not in kwargs:
            kwargs["config_json"] = "{}"
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<OrgInstalledTool(id={self.id!r}, org_id={self.org_id!r}, tool_id={self.tool_id!r})>"


class MarketplaceSkill(Base):
    """A skill available in the skills marketplace.

    Stores the skill's metadata and SKILL.md content template.

    Attributes:
        id: UUID primary key.
        name: Display name of the skill.
        description: Human-readable description.
        category: Skill category (e.g. "research", "coding", "writing").
        skill_content: The SKILL.md content for this skill.
        is_public: Whether the skill is visible in the public catalog.
        created_at: Timestamp of creation.
    """

    __tablename__ = "marketplace_skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, insert_default="")
    category: Mapped[str] = mapped_column(String(50), nullable=False, insert_default="research")
    skill_content: Mapped[str] = mapped_column(Text, nullable=False, insert_default="")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "description" not in kwargs:
            kwargs["description"] = ""
        if "category" not in kwargs:
            kwargs["category"] = "research"
        if "skill_content" not in kwargs:
            kwargs["skill_content"] = ""
        if "is_public" not in kwargs:
            kwargs["is_public"] = True
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<MarketplaceSkill(id={self.id!r}, name={self.name!r}, category={self.category!r})>"


class OrgInstalledSkill(Base):
    """Tracks which marketplace skills an organization has installed.

    Attributes:
        id: UUID primary key.
        org_id: Foreign key to organizations.id.
        skill_id: Foreign key to marketplace_skills.id.
        installed_at: Timestamp of installation.
    """

    __tablename__ = "org_installed_skills"
    __table_args__ = (UniqueConstraint("org_id", "skill_id", name="uq_org_skill"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id: Mapped[str] = mapped_column(String(36), ForeignKey("marketplace_skills.id", ondelete="CASCADE"), nullable=False, index=True)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization: Mapped["Organization"] = relationship("Organization")
    skill: Mapped["MarketplaceSkill"] = relationship("MarketplaceSkill")

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<OrgInstalledSkill(id={self.id!r}, org_id={self.org_id!r}, skill_id={self.skill_id!r})>"
