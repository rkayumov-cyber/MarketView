import axios from "axios";

const api = axios.create({
  baseURL: "/",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// ── Health ──────────────────────────────────────────────

export async function getHealth() {
  const { data } = await api.get("/health");
  return data;
}

export async function getHealthDetailed() {
  const { data } = await api.get("/health/detailed");
  return data;
}

// ── FRED Data ───────────────────────────────────────────

export async function getFredSeries() {
  const { data } = await api.get("/api/v1/data/fred/series");
  return data;
}

export async function getFredSeriesData(
  seriesName: string,
  startDate?: string,
  endDate?: string,
) {
  const params: Record<string, string> = {};
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const { data } = await api.get(`/api/v1/data/fred/series/${seriesName}`, {
    params,
  });
  return data;
}

export async function getFredInflation() {
  const { data } = await api.get("/api/v1/data/fred/inflation");
  return data;
}

export async function getFredRates() {
  const { data } = await api.get("/api/v1/data/fred/rates");
  return data;
}

export async function getFredLabor() {
  const { data } = await api.get("/api/v1/data/fred/labor");
  return data;
}

export async function getFredGrowth() {
  const { data } = await api.get("/api/v1/data/fred/growth");
  return data;
}

export async function getFredCredit() {
  const { data } = await api.get("/api/v1/data/fred/credit");
  return data;
}

export async function getFredYieldCurve() {
  const { data } = await api.get("/api/v1/data/fred/yield-curve");
  return data;
}

// ── Reports ─────────────────────────────────────────────

export interface ReportRequest {
  level: 1 | 2 | 3;
  format: "markdown" | "json" | "pdf" | "html";
  include_technicals?: boolean;
  include_sentiment?: boolean;
  include_correlations?: boolean;
  include_research?: boolean;
  assets?: string[];
  document_ids?: string[];
  title?: string;
  llm_provider?: string;
  llm_model?: string;
  custom_prompt?: string;
}

export interface LLMProvider {
  id: string;
  label: string;
  type: "closed" | "open";
  needs_key: boolean;
  models: string[];
  default_model: string;
  available: boolean;
}

export async function generateReport(config: ReportRequest) {
  const timeout = config.llm_provider ? 120000 : 30000;
  const { data } = await api.post("/api/v1/reports/generate", config, {
    timeout,
  });
  return data;
}

export async function getLLMProviders() {
  const { data } = await api.get("/api/v1/reports/llm-providers");
  return data as { providers: LLMProvider[] };
}

export async function getQuickReport(level: 1 | 2 | 3 = 1) {
  const { data } = await api.get("/api/v1/reports/generate/quick", {
    params: { level },
  });
  return data;
}

export async function getReport(reportId: string) {
  const { data } = await api.get(`/api/v1/reports/${reportId}`);
  return data;
}

export async function listReports(limit = 10, offset = 0) {
  const { data } = await api.get("/api/v1/reports/", {
    params: { limit, offset },
  });
  return data;
}

export async function deleteReport(reportId: string) {
  const { data } = await api.delete(`/api/v1/reports/${reportId}`);
  return data;
}

export function getDownloadUrl(reportId: string, format = "markdown") {
  return `/api/v1/reports/${reportId}/download?format=${format}`;
}

// ── Prompt Templates ───────────────────────────────────────

export interface PromptTemplate {
  template_id: string;
  name: string;
  description: string | null;
  prompt_text: string;
  is_default: boolean;
  created_at: string;
  updated_at: string | null;
}

export async function listTemplates() {
  const { data } = await api.get("/api/v1/templates/");
  return data as { templates: PromptTemplate[]; total: number };
}

export async function createTemplate(body: {
  name: string;
  description?: string;
  prompt_text: string;
}) {
  const { data } = await api.post("/api/v1/templates/", body);
  return data as PromptTemplate;
}

export async function updateTemplate(
  templateId: string,
  body: { name?: string; description?: string; prompt_text?: string },
) {
  const { data } = await api.put(`/api/v1/templates/${templateId}`, body);
  return data as PromptTemplate;
}

export async function deleteTemplate(templateId: string) {
  const { data } = await api.delete(`/api/v1/templates/${templateId}`);
  return data;
}

// ── Market Data ────────────────────────────────────────────

export type MarketDataSource = "live" | "mock";

export async function getMarketSnapshot(source: MarketDataSource = "live") {
  const { data } = await api.get("/api/v1/data/market/snapshot", {
    params: { source },
  });
  return data;
}

export async function getEquities(source: MarketDataSource = "live") {
  const { data } = await api.get("/api/v1/data/market/equities", {
    params: { source },
  });
  return data;
}

export async function getFx(source: MarketDataSource = "live") {
  const { data } = await api.get("/api/v1/data/market/fx", {
    params: { source },
  });
  return data;
}

export async function getCommodities(source: MarketDataSource = "live") {
  const { data } = await api.get("/api/v1/data/market/commodities", {
    params: { source },
  });
  return data;
}

export async function getCrypto(source: MarketDataSource = "live") {
  const { data } = await api.get("/api/v1/data/market/crypto", {
    params: { source },
  });
  return data;
}

// ── Reddit Sentiment ──────────────────────────────────────

export async function getRedditSentiment(source: MarketDataSource = "live") {
  const { data } = await api.get("/api/v1/reddit/sentiment", {
    params: { source },
  });
  return data;
}

export async function getRedditPosts(source: MarketDataSource = "live") {
  const { data } = await api.get("/api/v1/reddit/posts", {
    params: { source },
  });
  return data;
}

export async function getRedditTrending(source: MarketDataSource = "live") {
  const { data } = await api.get("/api/v1/reddit/trending", {
    params: { source },
  });
  return data;
}

// ── Data Sources ───────────────────────────────────────────

export interface DocumentMeta {
  id: number;
  document_id: string;
  filename: string;
  title: string | null;
  source_type: string;
  page_count: number | null;
  chunk_count: number;
  file_size: number | null;
  uploaded_at: string;
  metadata: Record<string, unknown> | null;
}

export interface SearchHit {
  text: string;
  document_id: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface EmbeddingProvider {
  id: string;
  label: string;
  needs_key: boolean;
  default_model: string;
  available: boolean;
}

export async function getProviders() {
  const { data } = await api.get("/api/v1/sources/providers");
  return data as { active: string; providers: EmbeddingProvider[] };
}

export async function uploadDocument(file: File, provider?: string) {
  const form = new FormData();
  form.append("file", file);
  const params: Record<string, string> = {};
  if (provider) params.provider = provider;
  const { data } = await api.post("/api/v1/sources/upload", form, {
    headers: { "Content-Type": undefined as unknown as string },
    params,
    timeout: 120000,
  });
  return data;
}

export async function ingestText(text: string, title?: string, provider?: string) {
  const { data } = await api.post("/api/v1/sources/ingest-text", {
    text,
    title: title || "Pasted text",
    provider: provider || undefined,
  });
  return data;
}

export async function listDocuments(limit = 50, offset = 0) {
  const { data } = await api.get("/api/v1/sources/documents", {
    params: { limit, offset },
  });
  return data as { documents: DocumentMeta[]; total: number };
}

export async function getDocument(documentId: string) {
  const { data } = await api.get(`/api/v1/sources/documents/${documentId}`);
  return data as DocumentMeta;
}

export async function deleteDocument(documentId: string) {
  const { data } = await api.delete(`/api/v1/sources/documents/${documentId}`);
  return data;
}

export async function searchDocuments(
  query: string,
  limit = 5,
  documentId?: string,
  provider?: string,
) {
  const { data } = await api.post("/api/v1/sources/search", {
    query,
    limit,
    document_id: documentId,
    provider: provider || undefined,
  });
  return data as { query: string; results: SearchHit[]; count: number };
}

export async function getSourcesStatus() {
  const { data } = await api.get("/api/v1/sources/status");
  return data;
}
