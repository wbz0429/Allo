import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock the config module
vi.mock("@/core/config", () => ({
  getBackendBaseURL: () => "http://localhost:8001",
}));

describe("knowledge API types", () => {
  it("KnowledgeBase interface has required fields", () => {
    const kb: import("./types").KnowledgeBase = {
      id: "kb-1",
      org_id: "org-1",
      name: "Test",
      description: "",
      chunk_size: 500,
      chunk_overlap: 50,
      embedding_model: "text-embedding-3-small",
      created_at: "2024-01-01",
      updated_at: "2024-01-01",
    };
    expect(kb.id).toBe("kb-1");
    expect(kb.chunk_size).toBe(500);
  });

  it("SearchResult has nested chunk structure", () => {
    const result: import("./types").SearchResult = {
      chunk: {
        id: "c-1",
        doc_id: "doc-1",
        kb_id: "kb-1",
        content: "Hello world",
        chunk_index: 0,
        metadata_json: "{}",
      },
      score: 0.95,
    };
    expect(result.chunk.id).toBe("c-1");
    expect(result.chunk.content).toBe("Hello world");
    expect(result.score).toBe(0.95);
  });

  it("KnowledgeDocument has status field", () => {
    const doc: import("./types").KnowledgeDocument = {
      id: "doc-1",
      kb_id: "kb-1",
      filename: "test.md",
      content_type: "text/markdown",
      chunk_count: 5,
      status: "ready",
      created_at: "2024-01-01",
    };
    expect(doc.status).toBe("ready");
  });

  it("CreateKnowledgeBaseRequest only requires name", () => {
    const req: import("./types").CreateKnowledgeBaseRequest = {
      name: "My KB",
    };
    expect(req.name).toBe("My KB");
    expect(req.description).toBeUndefined();
  });
});

describe("knowledge API functions", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("listKnowledgeBases calls correct endpoint", async () => {
    const mockResponse = {
      knowledge_bases: [
        { id: "kb-1", org_id: "org-1", name: "Test", description: "", chunk_size: 500, chunk_overlap: 50, embedding_model: "text-embedding-3-small", document_count: 0, created_at: "", updated_at: "" },
      ],
    };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const { listKnowledgeBases } = await import("./api");
    const result = await listKnowledgeBases();

    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8001/api/knowledge-bases",
      { credentials: "include" },
    );
    expect(result).toEqual(mockResponse.knowledge_bases);
  });

  it("listKnowledgeBases throws on error", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      statusText: "Internal Server Error",
    });

    const { listKnowledgeBases } = await import("./api");
    await expect(listKnowledgeBases()).rejects.toThrow("Failed to load knowledge bases");
  });

  it("deleteKnowledgeBase calls DELETE", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true });

    const { deleteKnowledgeBase } = await import("./api");
    await deleteKnowledgeBase("kb-1");

    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8001/api/knowledge-bases/kb-1",
      { method: "DELETE", credentials: "include" },
    );
  });

  it("searchKnowledgeBase sends POST with query", async () => {
    const mockResults = {
      results: [{ id: "c-1", content: "Hi", score: 0.9, chunk_index: 0, doc_id: "doc-1" }],
    };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResults),
    });

    const { searchKnowledgeBase } = await import("./api");
    const result = await searchKnowledgeBase("kb-1", "test query", 5);

    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8001/api/knowledge-bases/kb-1/search",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ query: "test query", top_k: 5 }),
      }),
    );
    expect(result).toEqual(mockResults.results);
  });
});
