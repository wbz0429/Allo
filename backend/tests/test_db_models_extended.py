"""Extended tests for all B2B database models beyond Organization/OrganizationMember."""

import uuid

from app.gateway.db.models import (
    Base,
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDocument,
    MarketplaceSkill,
    MarketplaceTool,
    OrgInstalledSkill,
    OrgInstalledTool,
    TenantConfig,
    UsageRecord,
)

# ---------------------------------------------------------------------------
# TenantConfig
# ---------------------------------------------------------------------------


class TestTenantConfig:
    def test_creation_with_defaults(self) -> None:
        tc = TenantConfig(org_id="org-1")
        assert tc.org_id == "org-1"
        assert tc.config_json == "{}"
        uuid.UUID(tc.id)

    def test_creation_with_explicit_values(self) -> None:
        tc = TenantConfig(id="tc-1", org_id="org-1", config_json='{"default_model": "gpt-4o"}')
        assert tc.id == "tc-1"
        assert tc.config_json == '{"default_model": "gpt-4o"}'

    def test_repr(self) -> None:
        tc = TenantConfig(id="tc-1", org_id="org-1")
        r = repr(tc)
        assert "TenantConfig" in r
        assert "tc-1" in r
        assert "org-1" in r

    def test_tablename(self) -> None:
        assert TenantConfig.__tablename__ == "tenant_configs"

    def test_columns(self) -> None:
        col_names = {c.name for c in TenantConfig.__table__.columns}
        assert col_names == {"id", "org_id", "config_json", "updated_at"}

    def test_org_id_unique(self) -> None:
        col = TenantConfig.__table__.columns["org_id"]
        assert col.unique is True

    def test_org_id_foreign_key(self) -> None:
        col = TenantConfig.__table__.columns["org_id"]
        fk_targets = [fk.target_fullname for fk in col.foreign_keys]
        assert "organizations.id" in fk_targets


# ---------------------------------------------------------------------------
# KnowledgeBase
# ---------------------------------------------------------------------------


class TestKnowledgeBase:
    def test_creation_with_defaults(self) -> None:
        kb = KnowledgeBase(org_id="org-1", name="Test KB")
        assert kb.name == "Test KB"
        assert kb.description == ""
        assert kb.chunk_size == 500
        assert kb.chunk_overlap == 50
        assert kb.embedding_model == "text-embedding-3-small"
        uuid.UUID(kb.id)

    def test_creation_with_explicit_values(self) -> None:
        kb = KnowledgeBase(
            id="kb-1",
            org_id="org-1",
            name="My KB",
            description="A test KB",
            chunk_size=1000,
            chunk_overlap=100,
            embedding_model="text-embedding-ada-002",
        )
        assert kb.id == "kb-1"
        assert kb.chunk_size == 1000
        assert kb.chunk_overlap == 100

    def test_repr(self) -> None:
        kb = KnowledgeBase(id="kb-1", org_id="org-1", name="My KB")
        r = repr(kb)
        assert "KnowledgeBase" in r
        assert "kb-1" in r
        assert "My KB" in r

    def test_tablename(self) -> None:
        assert KnowledgeBase.__tablename__ == "knowledge_bases"

    def test_columns(self) -> None:
        col_names = {c.name for c in KnowledgeBase.__table__.columns}
        expected = {"id", "org_id", "name", "description", "chunk_size", "chunk_overlap", "embedding_model", "created_at", "updated_at"}
        assert col_names == expected

    def test_org_id_indexed(self) -> None:
        col = KnowledgeBase.__table__.columns["org_id"]
        assert col.index is True

    def test_has_documents_relationship(self) -> None:
        mapper = KnowledgeBase.__mapper__
        assert "documents" in mapper.relationships

    def test_cascade_delete_orphan_on_documents(self) -> None:
        rel = KnowledgeBase.__mapper__.relationships["documents"]
        assert "delete" in rel.cascade
        assert "delete-orphan" in rel.cascade


# ---------------------------------------------------------------------------
# KnowledgeDocument
# ---------------------------------------------------------------------------


class TestKnowledgeDocument:
    def test_creation_with_defaults(self) -> None:
        doc = KnowledgeDocument(kb_id="kb-1", filename="test.md", content_type="text/markdown")
        assert doc.content_md == ""
        assert doc.chunk_count == 0
        assert doc.status == "processing"
        uuid.UUID(doc.id)

    def test_repr(self) -> None:
        doc = KnowledgeDocument(id="doc-1", kb_id="kb-1", filename="test.md", content_type="text/markdown")
        r = repr(doc)
        assert "KnowledgeDocument" in r
        assert "doc-1" in r
        assert "test.md" in r

    def test_tablename(self) -> None:
        assert KnowledgeDocument.__tablename__ == "knowledge_documents"

    def test_columns(self) -> None:
        col_names = {c.name for c in KnowledgeDocument.__table__.columns}
        expected = {"id", "kb_id", "filename", "content_type", "content_md", "chunk_count", "status", "created_at"}
        assert col_names == expected

    def test_kb_id_indexed(self) -> None:
        col = KnowledgeDocument.__table__.columns["kb_id"]
        assert col.index is True

    def test_has_chunks_relationship(self) -> None:
        mapper = KnowledgeDocument.__mapper__
        assert "chunks" in mapper.relationships

    def test_cascade_delete_orphan_on_chunks(self) -> None:
        rel = KnowledgeDocument.__mapper__.relationships["chunks"]
        assert "delete" in rel.cascade
        assert "delete-orphan" in rel.cascade


# ---------------------------------------------------------------------------
# KnowledgeChunk
# ---------------------------------------------------------------------------


class TestKnowledgeChunk:
    def test_creation_with_defaults(self) -> None:
        chunk = KnowledgeChunk(doc_id="doc-1", kb_id="kb-1", content="Hello", chunk_index=0)
        assert chunk.embedding == "[]"
        assert chunk.metadata_json == "{}"
        uuid.UUID(chunk.id)

    def test_creation_with_explicit_values(self) -> None:
        chunk = KnowledgeChunk(
            id="ch-1",
            doc_id="doc-1",
            kb_id="kb-1",
            content="Hello world",
            chunk_index=3,
            embedding="[0.1, 0.2]",
            metadata_json='{"key": "val"}',
        )
        assert chunk.id == "ch-1"
        assert chunk.chunk_index == 3
        assert chunk.embedding == "[0.1, 0.2]"

    def test_repr(self) -> None:
        chunk = KnowledgeChunk(id="ch-1", doc_id="doc-1", kb_id="kb-1", content="x", chunk_index=0)
        r = repr(chunk)
        assert "KnowledgeChunk" in r
        assert "ch-1" in r

    def test_tablename(self) -> None:
        assert KnowledgeChunk.__tablename__ == "knowledge_chunks"

    def test_doc_id_indexed(self) -> None:
        col = KnowledgeChunk.__table__.columns["doc_id"]
        assert col.index is True

    def test_kb_id_indexed(self) -> None:
        col = KnowledgeChunk.__table__.columns["kb_id"]
        assert col.index is True


# ---------------------------------------------------------------------------
# UsageRecord
# ---------------------------------------------------------------------------


class TestUsageRecord:
    def test_creation_with_defaults(self) -> None:
        rec = UsageRecord(org_id="org-1", user_id="u-1", record_type="api_call")
        assert rec.input_tokens == 0
        assert rec.output_tokens == 0
        assert rec.duration_seconds == 0.0
        uuid.UUID(rec.id)

    def test_creation_with_explicit_values(self) -> None:
        rec = UsageRecord(
            id="ur-1",
            org_id="org-1",
            user_id="u-1",
            record_type="llm_token",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=200,
            endpoint="/api/chat",
            duration_seconds=1.5,
        )
        assert rec.model_name == "gpt-4o"
        assert rec.input_tokens == 100
        assert rec.output_tokens == 200
        assert rec.duration_seconds == 1.5

    def test_repr(self) -> None:
        rec = UsageRecord(id="ur-1", org_id="org-1", user_id="u-1", record_type="api_call")
        r = repr(rec)
        assert "UsageRecord" in r
        assert "ur-1" in r
        assert "api_call" in r

    def test_tablename(self) -> None:
        assert UsageRecord.__tablename__ == "usage_records"

    def test_columns(self) -> None:
        col_names = {c.name for c in UsageRecord.__table__.columns}
        expected = {"id", "org_id", "user_id", "record_type", "model_name", "input_tokens", "output_tokens", "endpoint", "duration_seconds", "created_at"}
        assert col_names == expected

    def test_org_id_indexed(self) -> None:
        col = UsageRecord.__table__.columns["org_id"]
        assert col.index is True

    def test_record_type_indexed(self) -> None:
        col = UsageRecord.__table__.columns["record_type"]
        assert col.index is True


# ---------------------------------------------------------------------------
# MarketplaceTool
# ---------------------------------------------------------------------------


class TestMarketplaceTool:
    def test_creation_with_defaults(self) -> None:
        tool = MarketplaceTool(name="Test Tool")
        assert tool.description == ""
        assert tool.category == "search"
        assert tool.icon == ""
        assert tool.mcp_config_json == "{}"
        assert tool.is_public is True
        uuid.UUID(tool.id)

    def test_creation_with_explicit_values(self) -> None:
        tool = MarketplaceTool(id="t-1", name="My Tool", category="code", is_public=False)
        assert tool.id == "t-1"
        assert tool.category == "code"
        assert tool.is_public is False

    def test_repr(self) -> None:
        tool = MarketplaceTool(id="t-1", name="My Tool")
        r = repr(tool)
        assert "MarketplaceTool" in r
        assert "t-1" in r
        assert "My Tool" in r

    def test_tablename(self) -> None:
        assert MarketplaceTool.__tablename__ == "marketplace_tools"

    def test_name_unique(self) -> None:
        col = MarketplaceTool.__table__.columns["name"]
        assert col.unique is True


# ---------------------------------------------------------------------------
# OrgInstalledTool
# ---------------------------------------------------------------------------


class TestOrgInstalledTool:
    def test_creation_with_defaults(self) -> None:
        oit = OrgInstalledTool(org_id="org-1", tool_id="t-1")
        assert oit.config_json == "{}"
        uuid.UUID(oit.id)

    def test_repr(self) -> None:
        oit = OrgInstalledTool(id="oit-1", org_id="org-1", tool_id="t-1")
        r = repr(oit)
        assert "OrgInstalledTool" in r
        assert "oit-1" in r

    def test_tablename(self) -> None:
        assert OrgInstalledTool.__tablename__ == "org_installed_tools"


# ---------------------------------------------------------------------------
# MarketplaceSkill
# ---------------------------------------------------------------------------


class TestMarketplaceSkill:
    def test_creation_with_defaults(self) -> None:
        skill = MarketplaceSkill(name="Test Skill")
        assert skill.description == ""
        assert skill.category == "research"
        assert skill.skill_content == ""
        assert skill.is_public is True
        uuid.UUID(skill.id)

    def test_creation_with_explicit_values(self) -> None:
        skill = MarketplaceSkill(id="s-1", name="My Skill", category="coding", is_public=False)
        assert skill.id == "s-1"
        assert skill.category == "coding"
        assert skill.is_public is False

    def test_repr(self) -> None:
        skill = MarketplaceSkill(id="s-1", name="My Skill")
        r = repr(skill)
        assert "MarketplaceSkill" in r
        assert "s-1" in r

    def test_tablename(self) -> None:
        assert MarketplaceSkill.__tablename__ == "marketplace_skills"

    def test_name_unique(self) -> None:
        col = MarketplaceSkill.__table__.columns["name"]
        assert col.unique is True


# ---------------------------------------------------------------------------
# OrgInstalledSkill
# ---------------------------------------------------------------------------


class TestOrgInstalledSkill:
    def test_creation_with_defaults(self) -> None:
        ois = OrgInstalledSkill(org_id="org-1", skill_id="s-1")
        uuid.UUID(ois.id)

    def test_repr(self) -> None:
        ois = OrgInstalledSkill(id="ois-1", org_id="org-1", skill_id="s-1")
        r = repr(ois)
        assert "OrgInstalledSkill" in r
        assert "ois-1" in r

    def test_tablename(self) -> None:
        assert OrgInstalledSkill.__tablename__ == "org_installed_skills"


# ---------------------------------------------------------------------------
# Base metadata completeness
# ---------------------------------------------------------------------------


class TestBaseMetadata:
    def test_all_b2b_tables_registered(self) -> None:
        table_names = set(Base.metadata.tables.keys())
        expected_tables = {
            "organizations",
            "organization_members",
            "tenant_configs",
            "knowledge_bases",
            "knowledge_documents",
            "knowledge_chunks",
            "usage_records",
            "marketplace_tools",
            "org_installed_tools",
            "marketplace_skills",
            "org_installed_skills",
        }
        assert expected_tables.issubset(table_names)
