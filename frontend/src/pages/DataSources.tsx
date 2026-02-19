import { useCallback, useEffect, useRef, useState } from "react";
import {
  uploadDocument,
  ingestText,
  listDocuments,
  deleteDocument,
  searchDocuments,
  getSourcesStatus,
  getProviders,
  type DocumentMeta,
  type SearchHit,
  type EmbeddingProvider,
} from "../api/client";

// ── Helpers ──────────────────────────────────────────────────

function formatBytes(bytes: number | null): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Types ────────────────────────────────────────────────────

interface SourceInfo {
  name: string;
  type: string;
  description: string;
  status: string;
  rate_limit?: string;
  cache_ttl?: string;
  documents?: number;
  chromadb?: { status: string; total_chunks: number };
}

// ── Fallback data when API is offline ────────────────────────

const FALLBACK_SOURCES: SourceInfo[] = [
  {
    name: "FRED",
    type: "tier1_core",
    description:
      "Federal Reserve Economic Data — official US macro indicators",
    status: "not_configured",
    rate_limit: "120/min",
    cache_ttl: "3600s",
  },
  {
    name: "Yahoo Finance",
    type: "market_data",
    description:
      "Equities, FX, commodities — real-time & historical prices",
    status: "available",
    rate_limit: "33/min",
    cache_ttl: "900s",
  },
  {
    name: "CoinGecko",
    type: "market_data",
    description: "Cryptocurrency prices, market caps, and volumes",
    status: "available",
    rate_limit: "30/min",
    cache_ttl: "300s",
  },
  {
    name: "Reddit",
    type: "tier2_sentiment",
    description: "Social sentiment from financial subreddits",
    status: "not_configured",
    rate_limit: "60/min",
    cache_ttl: "900s",
  },
  {
    name: "Research Documents (RAG)",
    type: "tier3_research",
    description:
      "Uploaded PDFs indexed with ChromaDB + OpenAI embeddings",
    status: "not_configured",
    documents: 0,
    chromadb: { status: "offline", total_chunks: 0 },
  },
];

// ── Status badge ─────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    available: "text-green-400 border-green-400/30",
    configured: "text-green-400 border-green-400/30",
    online: "text-green-400 border-green-400/30",
    not_configured: "text-yellow-400 border-yellow-400/30",
    offline: "text-red-400 border-red-400/30",
  };
  const cls = colors[status] ?? "text-terminal-muted border-terminal-border";
  return (
    <span className={`text-[10px] uppercase tracking-wider border px-1.5 py-0.5 rounded ${cls}`}>
      {status.replace("_", " ")}
    </span>
  );
}

// ── Tier badge ───────────────────────────────────────────────

function TierBadge({ type }: { type: string }) {
  const labels: Record<string, string> = {
    tier1_core: "Tier 1",
    market_data: "Tier 1",
    tier2_sentiment: "Tier 2",
    tier3_research: "Tier 3",
  };
  return (
    <span className="text-[10px] text-terminal-muted tracking-wider bg-terminal-accent/10 px-1.5 py-0.5 rounded">
      {labels[type] ?? type}
    </span>
  );
}

// ── Main Component ──────────────────────────────────────────

export default function DataSources() {
  // State — embedding provider
  const [providers, setProviders] = useState<EmbeddingProvider[]>([]);
  const [activeProvider, setActiveProvider] = useState("local");
  const [selectedProvider, setSelectedProvider] = useState("local");

  // State — sources
  const [sources, setSources] = useState<SourceInfo[]>(FALLBACK_SOURCES);

  // State — documents
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [docTotal, setDocTotal] = useState(0);

  // State — upload
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  // State — paste text
  const [pasteText, setPasteText] = useState("");
  const [pasteTitle, setPasteTitle] = useState("");
  const [pasting, setPasting] = useState(false);
  const [pasteError, setPasteError] = useState<string | null>(null);

  // State — search
  const [searchQuery, setSearchQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchHit[]>([]);

  // ── Fetch data ──────────────────────────────────────────

  const fetchProviders = useCallback(async () => {
    try {
      const resp = await getProviders();
      setProviders(resp.providers);
      setActiveProvider(resp.active);
      setSelectedProvider(resp.active);
    } catch {
      /* offline — keep defaults */
    }
  }, []);

  const fetchSources = useCallback(async () => {
    try {
      const resp = await getSourcesStatus();
      if (resp?.sources) setSources(resp.sources);
    } catch {
      /* keep fallback */
    }
  }, []);

  const fetchDocuments = useCallback(async () => {
    try {
      const resp = await listDocuments();
      setDocuments(resp.documents);
      setDocTotal(resp.total);
    } catch {
      /* offline */
    }
  }, []);

  useEffect(() => {
    fetchProviders();
    fetchSources();
    fetchDocuments();
  }, [fetchProviders, fetchSources, fetchDocuments]);

  // ── Upload handler ──────────────────────────────────────

  const handleUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadError("Only PDF files are supported");
      return;
    }
    setUploading(true);
    setUploadError(null);
    try {
      await uploadDocument(file, selectedProvider);
      await fetchDocuments();
      await fetchSources();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Upload failed";
      setUploadError(msg);
    } finally {
      setUploading(false);
    }
  };

  const onFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
    e.target.value = "";
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  // ── Paste text handler ───────────────────────────────────

  const handlePasteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pasteText.trim()) return;
    setPasting(true);
    setPasteError(null);
    try {
      await ingestText(pasteText.trim(), pasteTitle.trim() || undefined, selectedProvider);
      setPasteText("");
      setPasteTitle("");
      await fetchDocuments();
      await fetchSources();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Ingest failed";
      setPasteError(msg);
    } finally {
      setPasting(false);
    }
  };

  // ── Delete handler ──────────────────────────────────────

  const handleDelete = async (documentId: string) => {
    try {
      await deleteDocument(documentId);
      await fetchDocuments();
      await fetchSources();
    } catch {
      /* ignore */
    }
  };

  // ── Search handler ──────────────────────────────────────

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const resp = await searchDocuments(searchQuery.trim(), 5, undefined, selectedProvider);
      setSearchResults(resp.results);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  // ── Render ──────────────────────────────────────────────

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-terminal-accent tracking-wide">
          DATA SOURCES
        </h1>
        <p className="text-sm text-terminal-muted mt-1">
          Live feeds, sentiment APIs, and uploaded research documents
        </p>
      </div>

      {/* ── Live Data Sources ─────────────────────────────── */}
      <section>
        <h2 className="text-sm font-semibold text-gray-300 tracking-wider mb-3 uppercase">
          Live Data Sources
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {sources.map((s) => (
            <div
              key={s.name}
              className="bg-terminal-surface border border-terminal-border rounded-lg p-4 flex flex-col gap-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-200">
                  {s.name}
                </span>
                <div className="flex items-center gap-2">
                  <TierBadge type={s.type} />
                  <StatusBadge status={s.status} />
                </div>
              </div>
              <p className="text-xs text-terminal-muted leading-relaxed">
                {s.description}
              </p>
              <div className="flex gap-4 text-[10px] text-terminal-muted mt-auto pt-2 border-t border-terminal-border">
                {s.rate_limit && <span>Rate: {s.rate_limit}</span>}
                {s.cache_ttl && <span>Cache: {s.cache_ttl}</span>}
                {s.documents != null && (
                  <span>Docs: {s.documents}</span>
                )}
                {s.chromadb && (
                  <span>Chunks: {s.chromadb.total_chunks}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Research Documents (RAG) ─────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-300 tracking-wider uppercase">
            Research Documents (RAG)
          </h2>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-terminal-muted uppercase tracking-wider">
              Embedding Model
            </span>
            <div className="flex rounded overflow-hidden border border-terminal-border">
              {(providers.length > 0
                ? providers
                : [
                    { id: "local", label: "Local", available: true },
                    { id: "openai", label: "OpenAI", available: false },
                    { id: "gemini", label: "Gemini", available: false },
                  ]
              ).map((p) => (
                <button
                  key={p.id}
                  onClick={() => setSelectedProvider(p.id)}
                  disabled={!p.available}
                  className={`px-3 py-1 text-[11px] transition-colors ${
                    selectedProvider === p.id
                      ? "bg-terminal-accent/20 text-terminal-accent"
                      : p.available
                        ? "text-terminal-muted hover:text-gray-300 hover:bg-white/[0.02]"
                        : "text-terminal-muted/40 cursor-not-allowed"
                  }`}
                  title={
                    !p.available
                      ? `${p.label} — API key not configured`
                      : p.id === activeProvider
                        ? `${p.label} (default)`
                        : p.label
                  }
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Upload dropzone */}
        <div
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer ${
            dragOver
              ? "border-terminal-accent bg-terminal-accent/5"
              : "border-terminal-border hover:border-terminal-accent/50"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => fileInput.current?.click()}
        >
          <input
            ref={fileInput}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={onFileSelect}
          />
          {uploading ? (
            <p className="text-sm text-terminal-accent animate-pulse">
              Processing PDF...
            </p>
          ) : (
            <>
              <p className="text-sm text-gray-300">
                Drop a PDF here or{" "}
                <span className="text-terminal-accent underline">
                  browse
                </span>
              </p>
              <p className="text-[10px] text-terminal-muted mt-1">
                Max 50 MB — text is extracted, chunked, and embedded for
                semantic search
              </p>
            </>
          )}
        </div>
        {uploadError && (
          <p className="text-xs text-red-400 mt-2">{uploadError}</p>
        )}

        {/* Paste text */}
        <form onSubmit={handlePasteSubmit} className="mt-4 space-y-2">
          <div className="flex gap-2">
            <input
              type="text"
              value={pasteTitle}
              onChange={(e) => setPasteTitle(e.target.value)}
              placeholder="Title (optional)"
              className="w-48 bg-terminal-surface border border-terminal-border rounded px-3 py-1.5 text-xs text-gray-200 placeholder:text-terminal-muted focus:outline-none focus:border-terminal-accent"
            />
            <button
              type="submit"
              disabled={pasting || !pasteText.trim()}
              className="ml-auto px-4 py-1.5 bg-terminal-accent/20 text-terminal-accent border border-terminal-accent/30 rounded text-xs hover:bg-terminal-accent/30 disabled:opacity-40 transition-colors"
            >
              {pasting ? "Processing..." : "Ingest Text"}
            </button>
          </div>
          <textarea
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            placeholder="Paste research text, notes, or articles here..."
            rows={5}
            className="w-full bg-terminal-surface border border-terminal-border rounded px-3 py-2 text-xs text-gray-200 placeholder:text-terminal-muted focus:outline-none focus:border-terminal-accent resize-y"
          />
          {pasteError && (
            <p className="text-xs text-red-400">{pasteError}</p>
          )}
        </form>

        {/* Document table */}
        {documents.length > 0 && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-terminal-muted text-left border-b border-terminal-border">
                  <th className="py-2 pr-4">Name</th>
                  <th className="py-2 pr-4">Type</th>
                  <th className="py-2 pr-4">Pages</th>
                  <th className="py-2 pr-4">Chunks</th>
                  <th className="py-2 pr-4">Size</th>
                  <th className="py-2 pr-4">Uploaded</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr
                    key={doc.document_id}
                    className="border-b border-terminal-border/50 hover:bg-white/[0.02]"
                  >
                    <td className="py-2 pr-4 text-gray-200 truncate max-w-[200px]">
                      {doc.filename}
                    </td>
                    <td className="py-2 pr-4 text-terminal-muted uppercase text-[10px]">
                      {doc.source_type}
                    </td>
                    <td className="py-2 pr-4 text-terminal-muted">
                      {doc.page_count ?? "—"}
                    </td>
                    <td className="py-2 pr-4 text-terminal-muted">
                      {doc.chunk_count}
                    </td>
                    <td className="py-2 pr-4 text-terminal-muted">
                      {formatBytes(doc.file_size)}
                    </td>
                    <td className="py-2 pr-4 text-terminal-muted">
                      {formatDate(doc.uploaded_at)}
                    </td>
                    <td className="py-2 text-right">
                      <button
                        onClick={() => handleDelete(doc.document_id)}
                        className="text-red-400/70 hover:text-red-400 transition-colors"
                        title="Delete document"
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-[10px] text-terminal-muted mt-2">
              {docTotal} document{docTotal !== 1 ? "s" : ""} total
            </p>
          </div>
        )}

        {/* Semantic Search */}
        <div className="mt-6">
          <h3 className="text-xs font-semibold text-gray-400 tracking-wider mb-2 uppercase">
            Semantic Search
          </h3>
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search across all documents..."
              className="flex-1 bg-terminal-surface border border-terminal-border rounded px-3 py-2 text-sm text-gray-200 placeholder:text-terminal-muted focus:outline-none focus:border-terminal-accent"
            />
            <button
              type="submit"
              disabled={searching || !searchQuery.trim()}
              className="px-4 py-2 bg-terminal-accent/20 text-terminal-accent border border-terminal-accent/30 rounded text-sm hover:bg-terminal-accent/30 disabled:opacity-40 transition-colors"
            >
              {searching ? "..." : "Search"}
            </button>
          </form>

          {searchResults.length > 0 && (
            <div className="mt-3 space-y-2">
              {searchResults.map((hit, i) => (
                <div
                  key={i}
                  className="bg-terminal-surface border border-terminal-border rounded p-3"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-terminal-muted">
                      doc:{hit.document_id} — page{" "}
                      {(hit.metadata?.page as number) ?? "?"}
                    </span>
                    <span className="text-[10px] text-terminal-accent">
                      {(hit.score * 100).toFixed(1)}% match
                    </span>
                  </div>
                  <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">
                    {hit.text}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
