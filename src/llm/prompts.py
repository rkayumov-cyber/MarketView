"""Prompt templates for LLM-enhanced report sections."""

from __future__ import annotations

SYSTEM_PROMPT = (
    "You are an institutional-grade market analyst writing for a hedge fund's "
    "daily briefing. Be concise, data-driven, and actionable. Avoid filler. "
    "Use a confident, professional tone. Reference specific data points."
)

_RESEARCH_INSTRUCTION = (
    "Incorporate relevant insights from the provided research documents "
    "into your analysis. Reference the source when citing specific findings."
)


def _format_research_context(chunks: list) -> str:
    """Format research chunks into a prompt block.

    Accepts a list of ResearchChunk-like objects (anything with .text,
    .source, and .page attributes).
    """
    if not chunks:
        return ""
    lines = ["RESEARCH CONTEXT:"]
    for i, chunk in enumerate(chunks, 1):
        page_str = f", p.{chunk.page}" if chunk.page else ""
        text_preview = chunk.text[:500]
        lines.append(f"[{i}] ({chunk.source}{page_str}): {text_preview}")
    return "\n".join(lines)


def _format_custom_prompt(custom_prompt: str | None) -> str:
    """Format custom focus instructions into a prompt block."""
    if not custom_prompt:
        return ""
    return (
        f"\n\nCUSTOM FOCUS INSTRUCTIONS:\n{custom_prompt}\n"
        "Prioritize these focus areas in your analysis."
    )


def pulse_narrative_prompt(
    regime: str,
    confidence: float,
    signals: list[str],
    sentiment_score: float | None = None,
    divergences: list[str] | None = None,
    research_context: list | None = None,
    custom_prompt: str | None = None,
) -> str:
    signals_text = "\n".join(f"- {s}" for s in signals)
    parts = [
        f"Market regime: {regime} (confidence: {confidence:.0%})",
        f"Key signals:\n{signals_text}",
    ]
    if sentiment_score is not None:
        parts.append(f"Sentiment score: {sentiment_score:.2f}")
    if divergences:
        parts.append(
            "Divergences:\n" + "\n".join(f"- {d}" for d in divergences)
        )
    data_block = "\n\n".join(parts)
    research_block = _format_research_context(research_context or [])
    extra = f"\n\n{research_block}\n\n{_RESEARCH_INSTRUCTION}" if research_block else ""
    extra += _format_custom_prompt(custom_prompt)
    return (
        f"Given the following market data, write a compelling 2-3 paragraph "
        f"narrative (the 'big picture') for today's market pulse. "
        f"Explain what the regime means, connect the signals, and highlight "
        f"what matters most for positioning.\n\n{data_block}{extra}"
    )


def pulse_takeaways_prompt(
    regime: str,
    big_narrative: str,
    existing_takeaways: list[str],
) -> str:
    takeaways_text = "\n".join(f"- {t}" for t in existing_takeaways)
    return (
        f"Current regime: {regime}\n"
        f"Narrative context: {big_narrative[:500]}\n"
        f"Rule-based takeaways:\n{takeaways_text}\n\n"
        f"Rewrite these takeaways to be sharper and more actionable. "
        f"Return exactly {len(existing_takeaways)} bullet points, "
        f"each on its own line starting with '- '. "
        f"Keep them under 20 words each."
    )


def macro_outlook_prompt(
    us_headline: str | None,
    eu_headline: str | None,
    asia_headline: str | None,
    existing_outlook: str,
    research_context: list | None = None,
    custom_prompt: str | None = None,
) -> str:
    parts = []
    if us_headline:
        parts.append(f"US: {us_headline}")
    if eu_headline:
        parts.append(f"EU: {eu_headline}")
    if asia_headline:
        parts.append(f"Asia: {asia_headline}")
    regions = "\n".join(parts) if parts else "No regional data available"
    research_block = _format_research_context(research_context or [])
    extra = f"\n\n{research_block}\n\n{_RESEARCH_INSTRUCTION}" if research_block else ""
    extra += _format_custom_prompt(custom_prompt)
    return (
        f"Regional macro summaries:\n{regions}\n\n"
        f"Current outlook: {existing_outlook}\n\n"
        f"Write a concise 2-3 sentence global macro outlook that synthesizes "
        f"these regional views into a coherent narrative. Focus on the "
        f"interplay between regions and what it means for global risk.{extra}"
    )


def macro_themes_prompt(
    existing_themes: list[str],
    outlook: str,
) -> str:
    themes_text = "\n".join(f"- {t}" for t in existing_themes)
    return (
        f"Global outlook: {outlook[:300]}\n"
        f"Rule-based themes:\n{themes_text}\n\n"
        f"Refine these cross-regional themes to be more insightful. "
        f"Return exactly {len(existing_themes)} themes, "
        f"each on its own line starting with '- '. "
        f"Make them specific and forward-looking."
    )


def sentiment_narrative_prompt(
    overall_score: float,
    bullish_ratio: float,
    total_posts: int,
    trending_tickers: list[tuple[str, int]],
    subreddit_summaries: list[str],
    contrarian_signals: list[str],
    research_context: list | None = None,
    custom_prompt: str | None = None,
) -> str:
    tickers_text = ", ".join(f"${t[0]} ({t[1]})" for t in trending_tickers[:8])
    subs_text = "\n".join(f"- {s}" for s in subreddit_summaries)
    contrarian_text = (
        "\n".join(f"- {c}" for c in contrarian_signals)
        if contrarian_signals
        else "None detected"
    )
    research_block = _format_research_context(research_context or [])
    extra = f"\n\n{research_block}\n\n{_RESEARCH_INSTRUCTION}" if research_block else ""
    extra += _format_custom_prompt(custom_prompt)
    return (
        f"Retail sentiment data from Reddit ({total_posts} posts analyzed):\n"
        f"- Overall score: {overall_score:+.2f}\n"
        f"- Bullish ratio: {bullish_ratio:.0%}\n"
        f"- Trending tickers: {tickers_text}\n\n"
        f"Per-subreddit breakdown:\n{subs_text}\n\n"
        f"Contrarian signals:\n{contrarian_text}\n\n"
        f"Write a 2-3 paragraph sentiment analysis narrative. Cover: "
        f"(1) the overall mood and what's driving it, "
        f"(2) notable divergences between communities, "
        f"(3) what this means for positioning — especially any contrarian "
        f"implications. Reference specific tickers and subreddits.{extra}"
    )


def forward_lesson_prompt(
    events: list[str],
    outlier_event: str,
    existing_lesson: str,
    research_context: list | None = None,
    custom_prompt: str | None = None,
) -> str:
    events_text = "\n".join(f"- {e}" for e in events[:5])
    research_block = _format_research_context(research_context or [])
    extra = f"\n\n{research_block}\n\n{_RESEARCH_INSTRUCTION}" if research_block else ""
    extra += _format_custom_prompt(custom_prompt)
    return (
        f"Upcoming events:\n{events_text}\n"
        f"Outlier scenario: {outlier_event}\n"
        f"Current lesson: {existing_lesson}\n\n"
        f"Write a thought-provoking 'lesson of the day' (2-3 sentences) "
        f"that ties the forward calendar to historical patterns or market "
        f"wisdom. Be specific and non-generic.{extra}"
    )
