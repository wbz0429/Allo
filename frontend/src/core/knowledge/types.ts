export interface KnowledgeBase {
  id: string;
  org_id: string;
  name: string;
  description: string;
  chunk_size: number;
  chunk_overlap: number;
  embedding_model: string;
  document_count?: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeDocument {
  id: string;
  kb_id: string;
  filename: string;
  content_type: string;
  file_size: number;
  index_status: "none" | "indexing" | "indexed" | "error";
  chunk_count: number;
  status: "ready" | "error";
  created_at: string;
}

export interface KnowledgeChunk {
  id: string;
  doc_id: string;
  kb_id: string;
  content: string;
  chunk_index: number;
  metadata_json: string;
}

export interface SearchResult {
  chunk: KnowledgeChunk;
  score: number;
}

export interface CreateKnowledgeBaseRequest {
  name: string;
  description?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  embedding_model?: string;
}

export interface UpdateKnowledgeBaseRequest {
  name?: string;
  description?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  embedding_model?: string;
}

export interface KeywordSearchResult {
  doc_id: string;
  filename: string;
  snippet: string;
  score: number;
}

export interface BuildIndexResult {
  indexed: number;
  failed: number;
  skipped: number;
}

export interface DocumentContent {
  content: string;
  filename: string;
}
