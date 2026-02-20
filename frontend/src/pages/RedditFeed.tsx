import { useState, useCallback } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import ChartCard from "../components/ChartCard";
import RefreshBar from "../components/RefreshBar";
import {
  getRedditSentiment,
  getRedditPosts,
  getRedditTrending,
} from "../api/client";
import { useDataSource } from "../context/DataSourceContext";
import { useAutoRefresh } from "../hooks/useAutoRefresh";

// ── Helpers ────────────────────────────────────────────────

function SourceBadge({ source }: { source: string }) {
  if (!source) return null;
  return (
    <span
      className={`text-[10px] px-2 py-0.5 rounded ml-2 ${
        source === "mock"
          ? "bg-amber-500/20 text-amber-400"
          : source.includes("fallback")
            ? "bg-orange-500/20 text-orange-400"
            : "bg-emerald-500/20 text-emerald-400"
      }`}
    >
      {source}
    </span>
  );
}

const tooltipStyle = {
  background: "#111827",
  border: "1px solid #1e293b",
  borderRadius: 6,
  fontSize: 12,
};

function sentimentColor(score: number): string {
  if (score >= 0.3) return "#22c55e";
  if (score >= 0.1) return "#86efac";
  if (score > -0.1) return "#94a3b8";
  if (score > -0.3) return "#f87171";
  return "#ef4444";
}

function sentimentLabel(score: number): string {
  if (score >= 0.3) return "Bullish";
  if (score >= 0.1) return "Slightly Bullish";
  if (score > -0.1) return "Neutral";
  if (score > -0.3) return "Slightly Bearish";
  return "Bearish";
}

// ── Sentiment Gauge ────────────────────────────────────────

function SentimentGauge({
  overall,
  source,
}: {
  overall: any;
  source: string;
}) {
  if (!overall) return null;
  const score = overall.overall_sentiment ?? 0;
  // Map -1..1 to 0..100%
  const pct = ((score + 1) / 2) * 100;
  const color = sentimentColor(score);

  return (
    <div className="card">
      <h3 className="text-sm font-semibold mb-4">
        Overall Reddit Sentiment
        <SourceBadge source={source} />
      </h3>

      {/* Gauge bar */}
      <div className="relative h-6 rounded-full bg-terminal-border overflow-hidden mb-4">
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
        <div className="absolute inset-0 flex items-center justify-center text-xs font-bold text-white drop-shadow">
          {score.toFixed(2)} — {sentimentLabel(score)}
        </div>
      </div>

      {/* Summary metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
        <div>
          <div className="text-terminal-muted text-xs">Sentiment Score</div>
          <div className="font-medium tabular-nums" style={{ color }}>
            {score.toFixed(3)}
          </div>
        </div>
        <div>
          <div className="text-terminal-muted text-xs">Bullish Ratio</div>
          <div className="font-medium tabular-nums">
            {((overall.overall_bullish_ratio ?? 0) * 100).toFixed(1)}%
          </div>
        </div>
        <div>
          <div className="text-terminal-muted text-xs">Posts Analyzed</div>
          <div className="font-medium tabular-nums">
            {overall.total_posts_analyzed ?? 0}
          </div>
        </div>
        <div>
          <div className="text-terminal-muted text-xs">Subreddits</div>
          <div className="font-medium tabular-nums">
            {overall.subreddit_count ?? 0}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Trending Tickers Chart ─────────────────────────────────

function TrendingChart({ tickers }: { tickers: any[] }) {
  if (!tickers || tickers.length === 0) return null;
  const data = tickers.slice(0, 15);
  const maxMentions = Math.max(...data.map((t: any) => t.mentions));

  return (
    <ChartCard title="Trending Tickers" subtitle="Mentions across all subreddits">
      <ResponsiveContainer width="100%" height={Math.max(300, data.length * 28)}>
        <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20 }}>
          <XAxis
            type="number"
            tick={{ fill: "#64748b", fontSize: 11 }}
            axisLine={{ stroke: "#1e293b" }}
            tickLine={false}
          />
          <YAxis
            dataKey="symbol"
            type="category"
            tick={{ fill: "#e2e8f0", fontSize: 12, fontWeight: 500 }}
            axisLine={false}
            tickLine={false}
            width={55}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(v: number) => [`${v} mentions`, "Count"]}
          />
          <Bar dataKey="mentions" radius={[0, 4, 4, 0]}>
            {data.map((entry: any, i: number) => (
              <Cell
                key={i}
                fill={`rgba(59, 130, 246, ${0.4 + (entry.mentions / maxMentions) * 0.6})`}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

// ── Subreddit Grid ─────────────────────────────────────────

function SubredditGrid({ subreddits }: { subreddits: Record<string, any> }) {
  if (!subreddits) return null;
  const entries = Object.values(subreddits);
  if (entries.length === 0) return null;

  return (
    <div>
      <h3 className="text-sm font-semibold mb-3">Subreddit Breakdown</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {entries.map((sub: any) => {
          const color = sentimentColor(sub.sentiment_score);
          return (
            <div
              key={sub.subreddit}
              className="card !p-3 space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-terminal-accent">
                  r/{sub.subreddit}
                </span>
                <span
                  className="text-[10px] font-medium px-1.5 py-0.5 rounded"
                  style={{ backgroundColor: `${color}20`, color }}
                >
                  {sub.sentiment_score?.toFixed(2)}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
                <div>
                  <span className="text-terminal-muted">Posts</span>{" "}
                  <span className="tabular-nums">{sub.post_count}</span>
                </div>
                <div>
                  <span className="text-terminal-muted">Avg Score</span>{" "}
                  <span className="tabular-nums">{sub.avg_score?.toFixed(0)}</span>
                </div>
                <div>
                  <span className="text-terminal-muted">Bullish</span>{" "}
                  <span className="tabular-nums">
                    {((sub.bullish_ratio ?? 0) * 100).toFixed(0)}%
                  </span>
                </div>
                <div>
                  <span className="text-terminal-muted">Avg Comments</span>{" "}
                  <span className="tabular-nums">{sub.avg_comments?.toFixed(0)}</span>
                </div>
              </div>
              {sub.top_tickers && sub.top_tickers.length > 0 && (
                <div className="flex flex-wrap gap-1 pt-1 border-t border-terminal-border">
                  {sub.top_tickers.slice(0, 5).map((t: any) => {
                    const [sym, cnt] = Array.isArray(t) ? t : [t.symbol, t.mentions];
                    return (
                      <span
                        key={sym}
                        className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400"
                      >
                        ${sym}
                        <span className="text-blue-400/60 ml-0.5">{cnt}</span>
                      </span>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Hot Posts Feed ──────────────────────────────────────────

function PostsFeed({ posts }: { posts: any[] }) {
  if (!posts || posts.length === 0) return null;

  return (
    <div>
      <h3 className="text-sm font-semibold mb-3">Hot Posts</h3>
      <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
        {posts.map((p: any, i: number) => (
          <a
            key={i}
            href={p.url}
            target="_blank"
            rel="noopener noreferrer"
            className="card !p-3 block hover:bg-white/[0.03] transition-colors group"
          >
            <div className="flex items-start gap-3">
              {/* Score */}
              <div className="shrink-0 w-12 text-center">
                <div className="text-sm font-bold tabular-nums text-terminal-accent">
                  {p.score >= 1000
                    ? `${(p.score / 1000).toFixed(1)}k`
                    : p.score}
                </div>
                <div className="text-[10px] text-terminal-muted">score</div>
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="text-sm leading-snug group-hover:text-blue-400 transition-colors">
                  {p.title}
                </div>
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-400">
                    r/{p.subreddit}
                  </span>
                  <span className="text-[10px] text-terminal-muted">
                    {p.num_comments} comments
                  </span>
                  {p.tickers?.map((t: string) => (
                    <span
                      key={t}
                      className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400"
                    >
                      ${t}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────

export default function RedditFeed() {
  const { source } = useDataSource();
  const [sentiment, setSentiment] = useState<any>(null);
  const [posts, setPosts] = useState<any>(null);
  const [trending, setTrending] = useState<any>(null);
  const [src, setSrc] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchReddit = useCallback(async () => {
    setLoading(true);
    try {
      const [sentRes, postsRes, trendRes] = await Promise.all([
        getRedditSentiment(source).catch(() => null),
        getRedditPosts(source).catch(() => null),
        getRedditTrending(source).catch(() => null),
      ]);
      if (sentRes) {
        setSentiment(sentRes.data);
        setSrc(sentRes.source);
      }
      if (postsRes) setPosts(postsRes.data);
      if (trendRes) setTrending(trendRes.data);
    } catch {
      // keep existing data
    } finally {
      setLoading(false);
    }
  }, [source]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(fetchReddit, {
    deps: [source],
  });

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold">Reddit Feed</h1>
          <p className="text-xs text-terminal-muted mt-1">
            Sentiment analysis across 8 finance subreddits
          </p>
        </div>
        <div className="flex items-center justify-center py-16 text-terminal-muted text-sm">
          <span className="animate-pulse">Loading Reddit data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Reddit Feed</h1>
        <div className="mt-1">
          <RefreshBar lastUpdated={lastUpdated} refreshing={refreshing} onRefresh={refresh} />
        </div>
      </div>

      {/* Sentiment Gauge */}
      <SentimentGauge overall={sentiment?.overall} source={src} />

      {/* Trending Tickers + Subreddit Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <TrendingChart tickers={trending?.tickers} />
        <SubredditGrid subreddits={sentiment?.subreddits} />
      </div>

      {/* Hot Posts */}
      <PostsFeed posts={posts?.posts} />
    </div>
  );
}
